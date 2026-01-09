/**
 * Cloudflare Email Worker for ABOKA AI
 * 
 * This worker receives emails sent to docs@tumai.us,
 * extracts attachments, and forwards them to the backend.
 */

export default {
  async email(message, env, ctx) {
    // Get email metadata
    const from = message.from;
    const to = message.to;
    const subject = message.headers.get("subject") || "";
    
    console.log(`📧 Email received from: ${from}, subject: ${subject}`);
    
    try {
      // Read the raw email
      const rawEmail = await new Response(message.raw).arrayBuffer();
      const emailText = new TextDecoder().decode(rawEmail);
      
      // Parse the email to extract attachments
      const attachments = await parseAttachments(emailText, rawEmail);
      
      console.log(`📎 Found ${attachments.length} attachment(s)`);
      
      // Prepare payload for backend
      const payload = {
        from: from,
        to: to,
        subject: subject,
        attachments: attachments,
        raw_size: rawEmail.byteLength,
        received_at: new Date().toISOString()
      };
      
      // Send to backend
      const backendUrl = env.BACKEND_URL || "https://aboka-ai-production.up.railway.app";
      const response = await fetch(`${backendUrl}/api/email/inbound-cloudflare`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Cloudflare-Email-Worker": "true",
          "Authorization": `Bearer ${env.WEBHOOK_SECRET || ""}`,
        },
        body: JSON.stringify(payload),
      });
      
      const result = await response.json();
      console.log(`✅ Backend response: ${response.status}`, result);
      
      if (!response.ok) {
        // Forward to fallback email if backend fails
        if (env.FALLBACK_EMAIL) {
          await message.forward(env.FALLBACK_EMAIL);
          console.log(`📨 Forwarded to fallback: ${env.FALLBACK_EMAIL}`);
        }
      }
      
    } catch (error) {
      console.error(`❌ Error processing email: ${error.message}`);
      
      // Forward to fallback on error
      if (env.FALLBACK_EMAIL) {
        await message.forward(env.FALLBACK_EMAIL);
      }
    }
  },
};

/**
 * Parse email to extract attachments
 * This is a simplified parser for MIME multipart emails
 */
async function parseAttachments(emailText, rawEmail) {
  const attachments = [];
  
  // Find the boundary from Content-Type header
  const boundaryMatch = emailText.match(/boundary="?([^"\r\n]+)"?/i);
  if (!boundaryMatch) {
    console.log("No multipart boundary found");
    return attachments;
  }
  
  const boundary = boundaryMatch[1];
  const parts = emailText.split(`--${boundary}`);
  
  for (const part of parts) {
    // Check if this part is an attachment
    const contentDisposition = part.match(/Content-Disposition:\s*attachment[^]*?filename="?([^"\r\n]+)"?/i);
    if (!contentDisposition) continue;
    
    const filename = contentDisposition[1];
    
    // Get content type
    const contentTypeMatch = part.match(/Content-Type:\s*([^\r\n;]+)/i);
    const contentType = contentTypeMatch ? contentTypeMatch[1].trim() : "application/octet-stream";
    
    // Get transfer encoding
    const encodingMatch = part.match(/Content-Transfer-Encoding:\s*([^\r\n]+)/i);
    const encoding = encodingMatch ? encodingMatch[1].trim().toLowerCase() : "";
    
    // Extract the content (after the double newline)
    const contentStart = part.indexOf("\r\n\r\n");
    if (contentStart === -1) continue;
    
    let content = part.substring(contentStart + 4);
    
    // Remove trailing boundary markers
    const boundaryEnd = content.indexOf(`--${boundary}`);
    if (boundaryEnd !== -1) {
      content = content.substring(0, boundaryEnd);
    }
    content = content.trim();
    
    // If already base64, use as-is; otherwise encode
    let base64Content;
    if (encoding === "base64") {
      // Remove any whitespace from base64 content
      base64Content = content.replace(/\s/g, "");
    } else {
      // Encode to base64
      const encoder = new TextEncoder();
      const bytes = encoder.encode(content);
      base64Content = btoa(String.fromCharCode(...bytes));
    }
    
    attachments.push({
      filename: filename,
      content_type: contentType,
      content: base64Content,
      size: base64Content.length * 0.75, // Approximate decoded size
    });
    
    console.log(`📄 Extracted attachment: ${filename} (${contentType})`);
  }
  
  return attachments;
}


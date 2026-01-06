import { NextRequest, NextResponse } from 'next/server';

// This endpoint now proxies to the Python backend instead of calling Supabase directly
// This keeps credentials secure and centralizes business logic

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080';

export async function GET(req: NextRequest) {
    const propertyId = req.nextUrl.searchParams.get('propertyId');
    if (!propertyId) {
        return NextResponse.json({ error: 'Property ID required' }, { status: 400 });
    }

    try {
        // Call the Python backend API for financial data
        const response = await fetch(`${BACKEND_URL}/api/numbers/${propertyId}`);
        
        if (!response.ok) {
            // If backend doesn't have this endpoint yet, return empty data
            if (response.status === 404) {
                return NextResponse.json({ 
                    ok: true, 
                    data: [],
                    message: 'Financial items endpoint not configured yet'
                });
            }
            const errorText = await response.text();
            return NextResponse.json({ error: errorText }, { status: response.status });
        }
        
        const data = await response.json();
        return NextResponse.json({ ok: true, data: data.items || data.data || [] });
        
    } catch (error: any) {
        console.error('Error fetching financials from backend:', error);
        // Return empty data instead of crashing - allows UI to still function
        return NextResponse.json({ 
            ok: true, 
            data: [],
            message: 'Could not connect to backend'
        });
    }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { id, propertyId, updates } = body;

    if (!id) {
        return NextResponse.json({ error: 'Missing ID' }, { status: 400 });
    }

    // Proxy to Python backend
    const response = await fetch(`${BACKEND_URL}/api/numbers/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, propertyId, updates })
    });
    
    if (!response.ok) {
        const errorText = await response.text();
        return NextResponse.json({ error: errorText }, { status: response.status });
    }
    
    const data = await response.json();
    return NextResponse.json({ ok: true, data: data });

  } catch (error: any) {
    console.error('Error updating financial item:', error);
    return NextResponse.json({ error: error.message || 'Internal Server Error' }, { status: 500 });
  }
}

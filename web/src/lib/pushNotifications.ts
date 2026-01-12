/**
 * Push Notifications Library for Aboka AI PWA
 */

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080';

/**
 * Check if push notifications are supported
 */
export function isPushSupported(): boolean {
  const supported = (
    typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  );
  console.log('[Push] isPushSupported:', supported);
  return supported;
}

/**
 * Get current notification permission status
 */
export function getNotificationPermission(): NotificationPermission | 'unsupported' {
  if (!isPushSupported()) return 'unsupported';
  return Notification.permission;
}

/**
 * Request notification permission from user
 */
export async function requestNotificationPermission(): Promise<NotificationPermission> {
  if (!isPushSupported()) {
    throw new Error('Push notifications not supported');
  }
  
  const permission = await Notification.requestPermission();
  return permission;
}

/**
 * Get VAPID public key from backend
 */
async function getVapidPublicKey(): Promise<string> {
  const response = await fetch(`${BACKEND_URL}/api/push/vapid-public-key`);
  const data = await response.json();
  
  if (!data.ok) {
    throw new Error(data.error || 'Failed to get VAPID key');
  }
  
  return data.publicKey;
}

/**
 * Convert VAPID key to Uint8Array for PushManager
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');
  
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  
  return outputArray;
}

/**
 * Helper to add timeout to promises
 */
function withTimeout<T>(promise: Promise<T>, ms: number, errorMsg: string): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) => 
      setTimeout(() => reject(new Error(errorMsg)), ms)
    )
  ]);
}

/**
 * Subscribe to push notifications
 */
export async function subscribeToPush(userIdentifier: string = 'default_user'): Promise<{ success: boolean; error?: string; step?: string }> {
  console.log('[Push] subscribeToPush called');
  
  if (!isPushSupported()) {
    console.warn('[Push] Not supported in this browser');
    return { success: false, error: 'Push no soportado en este navegador', step: 'support-check' };
  }
  
  try {
    // Step 1: Request permission
    console.log('[Push] Step 1: Requesting permission...');
    const permission = await withTimeout(
      requestNotificationPermission(),
      10000,
      'Timeout: El diálogo de permisos no apareció. Ve a Ajustes > Aboka > Notificaciones y actívalas manualmente.'
    );
    console.log('[Push] Permission result:', permission);
    
    if (permission !== 'granted') {
      console.warn('[Push] Permission denied');
      return { success: false, error: 'Permiso denegado. Ve a Ajustes > Aboka > Notificaciones.', step: 'permission' };
    }
    
    // Step 2: Get service worker
    console.log('[Push] Step 2: Getting service worker...');
    const registration = await withTimeout(
      navigator.serviceWorker.ready,
      10000,
      'Timeout: Service Worker no está listo. Intenta recargar la app.'
    );
    console.log('[Push] Service worker ready');
    
    // Step 3: Get VAPID key from backend
    console.log('[Push] Step 3: Fetching VAPID key...');
    const vapidPublicKey = await withTimeout(
      getVapidPublicKey(),
      10000,
      'Timeout: No se pudo conectar al servidor. Verifica tu conexión.'
    );
    console.log('[Push] Got VAPID key:', vapidPublicKey.substring(0, 20) + '...');
    
    // Step 4: Subscribe to PushManager
    console.log('[Push] Step 4: Subscribing to PushManager...');
    const subscription = await withTimeout(
      registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
      }),
      15000,
      'Timeout: PushManager no respondió. Este navegador puede no soportar push notifications.'
    );
    console.log('[Push] PushManager subscription created');
    
    // Step 5: Send to backend
    console.log('[Push] Step 5: Sending to backend...');
    const response = await withTimeout(
      fetch(`${BACKEND_URL}/api/push/subscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_identifier: userIdentifier,
          subscription: subscription.toJSON()
        })
      }),
      10000,
      'Timeout: El servidor no respondió. Intenta de nuevo.'
    );
    
    console.log('[Push] Backend response status:', response.status);
    const data = await response.json();
    console.log('[Push] Backend response:', data);
    
    if (data.ok) {
      console.log('[Push] ✅ Successfully subscribed!');
      return { success: true, step: 'complete' };
    } else {
      return { success: false, error: data.error || 'Error del servidor', step: 'backend' };
    }
    
  } catch (error) {
    console.error('[Push] Error:', error);
    const errorMessage = error instanceof Error ? error.message : 'Error desconocido';
    return { success: false, error: errorMessage, step: 'unknown' };
  }
}

/**
 * Re-sync local subscription with backend (call on app load)
 */
export async function resyncSubscription(userIdentifier: string = 'default_user'): Promise<boolean> {
  console.log('[Push] resyncSubscription called');
  
  if (!isPushSupported()) return false;
  
  try {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    
    if (!subscription) {
      console.log('[Push] No local subscription to resync');
      return false;
    }
    
    console.log('[Push] Found local subscription, resyncing with backend...');
    
    const response = await fetch(`${BACKEND_URL}/api/push/subscribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_identifier: userIdentifier,
        subscription: subscription.toJSON()
      })
    });
    
    const data = await response.json();
    console.log('[Push] Resync result:', data.ok ? 'success' : 'failed');
    return data.ok;
    
  } catch (error) {
    console.error('[Push] Resync error:', error);
    return false;
  }
}

/**
 * Unsubscribe from push notifications
 */
export async function unsubscribeFromPush(): Promise<boolean> {
  if (!isPushSupported()) return false;
  
  try {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    
    if (!subscription) {
      console.log('[Push] No subscription to unsubscribe');
      return true;
    }
    
    // Unsubscribe locally
    await subscription.unsubscribe();
    
    // Tell backend
    await fetch(`${BACKEND_URL}/api/push/unsubscribe`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ endpoint: subscription.endpoint })
    });
    
    console.log('[Push] Successfully unsubscribed');
    return true;
    
  } catch (error) {
    console.error('[Push] Error unsubscribing:', error);
    return false;
  }
}

/**
 * Check if currently subscribed to push
 */
export async function isSubscribedToPush(): Promise<boolean> {
  if (!isPushSupported()) return false;
  
  try {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    return subscription !== null;
  } catch {
    return false;
  }
}

/**
 * Show a local notification (for testing)
 */
export async function showLocalNotification(title: string, body: string): Promise<void> {
  if (!isPushSupported()) return;
  
  const permission = Notification.permission;
  if (permission !== 'granted') return;
  
  const registration = await navigator.serviceWorker.ready;
  await registration.showNotification(title, {
    body,
    icon: '/icon-192.png',
    badge: '/badge-72.png'
  } as NotificationOptions);
}


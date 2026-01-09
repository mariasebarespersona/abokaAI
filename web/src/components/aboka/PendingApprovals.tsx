'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  Check,
  X,
  Eye,
  RefreshCw,
  Inbox,
  Bell,
  BellOff,
  Clock,
  Building2,
  FolderOpen,
  AlertCircle
} from 'lucide-react';
import { 
  isPushSupported, 
  getNotificationPermission, 
  subscribeToPush, 
  isSubscribedToPush 
} from '@/lib/pushNotifications';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface PendingApproval {
  id: string;
  property_id: string;
  property_name: string;
  document_hint: string;
  suggested_cajon: string | null;
  suggested_subcajon: string | null;
  suggested_document_name: string | null;
  temp_storage_path: string;
  original_filename: string;
  content_type: string;
  sender_email: string | null;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  preview_url?: string;
}

interface PendingApprovalsProps {
  onApprovalProcessed?: () => void;
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export function PendingApprovals({ onApprovalProcessed }: PendingApprovalsProps) {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  
  // Push notification state
  const [pushSupported, setPushSupported] = useState(false);
  const [pushPermission, setPushPermission] = useState<NotificationPermission | 'unsupported'>('default');
  const [isSubscribed, setIsSubscribed] = useState(false);

  const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080';

  // Fetch pending approvals
  const fetchApprovals = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    else setIsRefreshing(true);
    setError(null);

    try {
      const response = await fetch(`${BACKEND_URL}/api/approvals/pending`);
      const data = await response.json();

      if (data.ok) {
        setApprovals(data.approvals || []);
      } else {
        setError(data.error || 'Error al cargar aprobaciones');
      }
    } catch (err) {
      console.error('Error fetching approvals:', err);
      setError('Error de conexión');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [BACKEND_URL]);

  // Check push notification status
  const checkPushStatus = useCallback(async () => {
    const supported = isPushSupported();
    setPushSupported(supported);
    
    if (supported) {
      setPushPermission(getNotificationPermission());
      const subscribed = await isSubscribedToPush();
      setIsSubscribed(subscribed);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchApprovals();
    checkPushStatus();

    // Listen for notification clicks
    const handleNotificationClick = (event: CustomEvent) => {
      console.log('Notification clicked:', event.detail);
      fetchApprovals(false);
    };

    window.addEventListener('notification-click', handleNotificationClick as EventListener);
    
    return () => {
      window.removeEventListener('notification-click', handleNotificationClick as EventListener);
    };
  }, [fetchApprovals, checkPushStatus]);

  // Enable push notifications
  const handleEnablePush = async () => {
    const success = await subscribeToPush();
    if (success) {
      setIsSubscribed(true);
      setPushPermission('granted');
    }
  };

  // Approve document
  const handleApprove = async (approval: PendingApproval) => {
    setProcessingId(approval.id);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/approvals/${approval.id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });

      const data = await response.json();

      if (data.ok) {
        // Remove from list
        setApprovals(prev => prev.filter(a => a.id !== approval.id));
        onApprovalProcessed?.();
      } else {
        setError(data.error || 'Error al aprobar');
      }
    } catch (err) {
      console.error('Error approving:', err);
      setError('Error de conexión');
    } finally {
      setProcessingId(null);
    }
  };

  // Reject document
  const handleReject = async (approval: PendingApproval) => {
    setProcessingId(approval.id);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/approvals/${approval.id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Rechazado por el usuario' })
      });

      const data = await response.json();

      if (data.ok) {
        setApprovals(prev => prev.filter(a => a.id !== approval.id));
        onApprovalProcessed?.();
      } else {
        setError(data.error || 'Error al rechazar');
      }
    } catch (err) {
      console.error('Error rejecting:', err);
      setError('Error de conexión');
    } finally {
      setProcessingId(null);
    }
  };

  // Format date
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <p className="mt-4 text-sm text-slate-500">Cargando aprobaciones...</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white rounded-xl border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-orange-600 to-amber-500">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center">
              <Inbox size={24} className="text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Aprobaciones Pendientes</h2>
              <p className="text-sm text-orange-100">
                {approvals.length} documento{approvals.length !== 1 ? 's' : ''} por revisar
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Push notifications toggle */}
            {pushSupported && (
              <button
                onClick={handleEnablePush}
                disabled={isSubscribed}
                className={`p-2.5 rounded-lg transition-colors ${
                  isSubscribed 
                    ? 'bg-white/20 text-white cursor-default' 
                    : 'bg-white/10 hover:bg-white/20 text-white'
                }`}
                title={isSubscribed ? 'Notificaciones activadas' : 'Activar notificaciones'}
              >
                {isSubscribed ? <Bell size={18} /> : <BellOff size={18} />}
              </button>
            )}
            <button
              onClick={() => fetchApprovals(false)}
              disabled={isRefreshing}
              className="p-2.5 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors disabled:opacity-50"
              title="Actualizar"
            >
              <RefreshCw size={18} className={isRefreshing ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
          <AlertCircle size={16} />
          <span className="text-sm">{error}</span>
          <button onClick={() => setError(null)} className="ml-auto">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {approvals.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400">
            <Inbox size={48} className="mb-4 opacity-30" />
            <h3 className="text-lg font-medium text-slate-500">Sin documentos pendientes</h3>
            <p className="text-sm text-center mt-2 max-w-xs">
              Los documentos enviados por email aparecerán aquí para tu aprobación
            </p>
            
            {/* Push notification CTA */}
            {pushSupported && !isSubscribed && (
              <button
                onClick={handleEnablePush}
                className="mt-6 flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
              >
                <Bell size={16} />
                Activar notificaciones
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {approvals.map((approval) => (
              <div
                key={approval.id}
                className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
                      <FileText size={20} className="text-orange-600" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-800">{approval.document_hint}</h4>
                      <div className="flex items-center gap-2 text-sm text-slate-500">
                        <Building2 size={12} />
                        <span>{approval.property_name}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-slate-400">
                    <Clock size={12} />
                    {formatDate(approval.created_at)}
                  </div>
                </div>

                {/* Details */}
                <div className="mb-4 p-3 bg-slate-50 rounded-lg">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-slate-500">Archivo:</span>
                      <p className="font-medium text-slate-700 truncate">{approval.original_filename}</p>
                    </div>
                    <div>
                      <span className="text-slate-500">Destino sugerido:</span>
                      <p className="font-medium text-slate-700">
                        {approval.suggested_cajon || '—'} / {approval.suggested_subcajon || '—'}
                      </p>
                    </div>
                  </div>
                  {approval.sender_email && (
                    <div className="mt-2 text-xs text-slate-400">
                      Enviado desde: {approval.sender_email}
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  {approval.preview_url && (
                    <button
                      onClick={() => setPreviewUrl(approval.preview_url!)}
                      className="flex items-center gap-2 px-3 py-2 text-sm bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors"
                    >
                      <Eye size={16} />
                      Ver documento
                    </button>
                  )}
                  <div className="flex-1" />
                  <button
                    onClick={() => handleReject(approval)}
                    disabled={processingId === approval.id}
                    className="flex items-center gap-2 px-4 py-2 text-sm bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50"
                  >
                    <X size={16} />
                    Rechazar
                  </button>
                  <button
                    onClick={() => handleApprove(approval)}
                    disabled={processingId === approval.id}
                    className="flex items-center gap-2 px-4 py-2 text-sm bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-50"
                  >
                    {processingId === approval.id ? (
                      <RefreshCw size={16} className="animate-spin" />
                    ) : (
                      <Check size={16} />
                    )}
                    Aprobar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Document Preview Modal */}
      {previewUrl && (
        <div 
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={() => setPreviewUrl(null)}
        >
          <div className="relative w-full max-w-4xl h-[80vh] bg-white rounded-xl overflow-hidden">
            <button
              onClick={() => setPreviewUrl(null)}
              className="absolute top-4 right-4 z-10 p-2 bg-slate-800 hover:bg-slate-700 rounded-full text-white"
            >
              <X size={20} />
            </button>
            <iframe
              src={previewUrl}
              className="w-full h-full"
              title="Document Preview"
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// BADGE COMPONENT (for showing count in sidebar)
// ═══════════════════════════════════════════════════════════════════════════════

interface ApprovalsBadgeProps {
  className?: string;
}

export function ApprovalsBadge({ className = '' }: ApprovalsBadgeProps) {
  const [count, setCount] = useState(0);
  const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080';

  useEffect(() => {
    const fetchCount = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/approvals/pending`);
        const data = await response.json();
        if (data.ok) {
          setCount(data.count || 0);
        }
      } catch (err) {
        console.error('Error fetching approval count:', err);
      }
    };

    fetchCount();
    
    // Poll every 30 seconds
    const interval = setInterval(fetchCount, 30000);
    
    return () => clearInterval(interval);
  }, [BACKEND_URL]);

  if (count === 0) return null;

  return (
    <span className={`inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 text-xs font-bold text-white bg-orange-500 rounded-full ${className}`}>
      {count > 99 ? '99+' : count}
    </span>
  );
}


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
  Monitor,
  ChevronDown,
  ChevronUp,
  DollarSign,
  Calculator
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

interface PendingExtraction {
  document_id: string;
  document_name: string;
  original_filename: string;
  cajon: string;
  subcajon: string;
  extracted_data: {
    concepto_detectado?: string;
    valor_total?: number;
    proveedor?: string;
    fecha?: string;
  };
  mapped_estudio_key: string | null;
  extraction_confidence: number;
  extracted_at: string;
  property_id: string;
  property_name: string;
}

// Human-readable labels for estudio keys
const ESTUDIO_LABELS: Record<string, string> = {
  'reforma_ac': 'Aire Acondicionado',
  'reforma_fontaneria': 'Fontanería',
  'reforma_electricidad': 'Electricidad',
  'reforma_albanileria': 'Albañilería',
  'reforma_pintura': 'Pintura',
  'reforma_cocina': 'Cocina',
  'reforma_bano': 'Baño',
  'reforma_suelos': 'Suelos',
  'reforma_ventanas': 'Ventanas',
  'reforma_carpinteria': 'Carpintería',
  'compra_notaria': 'Notaría',
  'compra_registro': 'Registro',
  'compra_gestoria': 'Gestoría',
  'compra_itp': 'ITP',
  'venta_comision': 'Comisión',
};

function getEstudioLabel(key: string | null): string {
  if (!key) return 'Sin asignar';
  return ESTUDIO_LABELS[key] || key.replace('_', ' ');
}

interface MobileApprovalsViewProps {
  onSwitchToDesktop: () => void;
  onApprovalProcessed?: () => void;
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export function MobileApprovalsView({ onSwitchToDesktop, onApprovalProcessed }: MobileApprovalsViewProps) {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [extractions, setExtractions] = useState<PendingExtraction[]>([]);
  const [activeTab, setActiveTab] = useState<'documents' | 'values'>('documents');
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  
  // Push notification state
  const [pushSupported, setPushSupported] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [subscribing, setSubscribing] = useState(false);

  const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080';

  // Fetch pending approvals and extractions
  const fetchApprovals = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    else setIsRefreshing(true);
    setError(null);

    try {
      // Fetch both in parallel
      const [approvalsRes, extractionsRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/approvals/pending`),
        fetch(`${BACKEND_URL}/api/extractions/pending`)
      ]);
      
      const approvalsData = await approvalsRes.json();
      const extractionsData = await extractionsRes.json();

      if (approvalsData.ok) {
        setApprovals(approvalsData.approvals || []);
      }
      
      if (extractionsData.ok) {
        setExtractions(extractionsData.extractions || []);
      }
      
      if (!approvalsData.ok && !extractionsData.ok) {
        setError('Error al cargar');
      }
    } catch (err) {
      console.error('Error fetching approvals:', err);
      setError('Sin conexión');
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
      const subscribed = await isSubscribedToPush();
      setIsSubscribed(subscribed);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchApprovals();
    checkPushStatus();

    // Listen for notification clicks
    const handleNotificationClick = () => {
      fetchApprovals(false);
    };

    window.addEventListener('notification-click', handleNotificationClick);
    
    return () => {
      window.removeEventListener('notification-click', handleNotificationClick);
    };
  }, [fetchApprovals, checkPushStatus]);

  // Enable push notifications
  const handleEnablePush = async () => {
    setSubscribing(true);
    const success = await subscribeToPush();
    if (success) {
      setIsSubscribed(true);
    }
    setSubscribing(false);
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
        setApprovals(prev => prev.filter(a => a.id !== approval.id));
        onApprovalProcessed?.();
      } else {
        setError(data.error || 'Error al aprobar');
      }
    } catch (err) {
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
        body: JSON.stringify({ reason: 'Rechazado' })
      });

      const data = await response.json();

      if (data.ok) {
        setApprovals(prev => prev.filter(a => a.id !== approval.id));
        onApprovalProcessed?.();
      } else {
        setError(data.error || 'Error al rechazar');
      }
    } catch (err) {
      setError('Error de conexión');
    } finally {
      setProcessingId(null);
    }
  };

  // Approve value extraction
  const handleApproveExtraction = async (extraction: PendingExtraction) => {
    setProcessingId(extraction.document_id);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/extractions/${extraction.document_id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });

      const data = await response.json();

      if (data.ok) {
        setExtractions(prev => prev.filter(e => e.document_id !== extraction.document_id));
        onApprovalProcessed?.();
      } else {
        setError(data.error || 'Error al aprobar valor');
      }
    } catch (err) {
      setError('Error de conexión');
    } finally {
      setProcessingId(null);
    }
  };

  // Reject value extraction
  const handleRejectExtraction = async (extraction: PendingExtraction) => {
    setProcessingId(extraction.document_id);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/extractions/${extraction.document_id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });

      const data = await response.json();

      if (data.ok) {
        setExtractions(prev => prev.filter(e => e.document_id !== extraction.document_id));
        onApprovalProcessed?.();
      } else {
        setError(data.error || 'Error al rechazar valor');
      }
    } catch (err) {
      setError('Error de conexión');
    } finally {
      setProcessingId(null);
    }
  };

  // Format date
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    
    if (diffMins < 1) return 'Ahora';
    if (diffMins < 60) return `Hace ${diffMins} min`;
    if (diffHours < 24) return `Hace ${diffHours}h`;
    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 text-white">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur-sm border-b border-slate-700 px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center font-bold text-lg shadow-lg">
              A
            </div>
            <div>
              <h1 className="font-bold text-lg">Aboka AI</h1>
              <p className="text-xs text-slate-400">Aprobaciones</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchApprovals(false)}
              disabled={isRefreshing}
              className="p-2.5 rounded-full bg-slate-800 hover:bg-slate-700 transition-colors"
            >
              <RefreshCw size={18} className={isRefreshing ? 'animate-spin' : ''} />
            </button>
            <button
              onClick={onSwitchToDesktop}
              className="p-2.5 rounded-full bg-slate-800 hover:bg-slate-700 transition-colors"
              title="Ver versión completa"
            >
              <Monitor size={18} />
            </button>
          </div>
        </div>
      </header>

      {/* Push Notification Banner */}
      {pushSupported && !isSubscribed && (
        <div className="mx-4 mt-4 p-4 bg-gradient-to-r from-orange-500 to-amber-500 rounded-xl">
          <div className="flex items-center gap-3">
            <Bell size={24} />
            <div className="flex-1">
              <p className="font-semibold">Activa las notificaciones</p>
              <p className="text-sm text-orange-100">Recibe alertas de nuevos documentos</p>
            </div>
            <button
              onClick={handleEnablePush}
              disabled={subscribing}
              className="px-4 py-2 bg-white text-orange-600 font-semibold rounded-lg text-sm"
            >
              {subscribing ? '...' : 'Activar'}
            </button>
          </div>
        </div>
      )}

      {/* Success banner when subscribed */}
      {isSubscribed && (
        <div className="mx-4 mt-4 p-3 bg-emerald-500/20 border border-emerald-500/30 rounded-xl flex items-center gap-2 text-emerald-400">
          <Bell size={16} />
          <span className="text-sm">Notificaciones activadas</span>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-500/20 border border-red-500/30 rounded-xl flex items-center gap-2 text-red-400">
          <span className="text-sm">{error}</span>
          <button onClick={() => setError(null)} className="ml-auto">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="px-4 pt-4">
        <div className="flex gap-2 bg-slate-800/50 p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('documents')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'documents'
                ? 'bg-orange-500 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <FileText size={16} />
            Documentos
            {approvals.length > 0 && (
              <span className="bg-white/20 px-1.5 py-0.5 rounded text-xs">{approvals.length}</span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('values')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'values'
                ? 'bg-emerald-500 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Calculator size={16} />
            Valores
            {extractions.length > 0 && (
              <span className="bg-white/20 px-1.5 py-0.5 rounded text-xs">{extractions.length}</span>
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      <main className="p-4">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
            <p className="mt-4 text-sm text-slate-400">Cargando...</p>
          </div>
        ) : activeTab === 'documents' ? (
          /* Documents Tab */
          approvals.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-20 h-20 bg-slate-800 rounded-full flex items-center justify-center mb-4">
                <Inbox size={36} className="text-slate-500" />
              </div>
              <h2 className="text-xl font-semibold text-slate-300">Sin documentos pendientes</h2>
              <p className="text-sm text-slate-500 mt-2 max-w-xs">
                Los documentos enviados por email aparecerán aquí
              </p>
              <p className="text-xs text-slate-600 mt-4">
                Envía a: <span className="text-blue-400">docs@tumai.us</span>
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-slate-400 mb-4">
                {approvals.length} documento{approvals.length !== 1 ? 's' : ''} pendiente{approvals.length !== 1 ? 's' : ''}
              </p>
              
              {approvals.map((approval) => (
                <div
                  key={approval.id}
                  className="bg-slate-800/50 border border-slate-700 rounded-2xl overflow-hidden"
                >
                  {/* Card Header - Always visible */}
                  <button
                    onClick={() => setExpandedId(expandedId === approval.id ? null : approval.id)}
                    className="w-full p-4 flex items-center gap-3 text-left"
                  >
                    <div className="w-12 h-12 rounded-xl bg-orange-500/20 flex items-center justify-center flex-shrink-0">
                      <FileText size={24} className="text-orange-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-white truncate">{approval.document_hint}</h3>
                      <div className="flex items-center gap-2 text-sm text-slate-400 mt-0.5">
                        <Building2 size={12} />
                        <span className="truncate">{approval.property_name}</span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className="text-xs text-slate-500">{formatDate(approval.created_at)}</span>
                      {expandedId === approval.id ? (
                        <ChevronUp size={16} className="text-slate-500" />
                      ) : (
                        <ChevronDown size={16} className="text-slate-500" />
                      )}
                    </div>
                  </button>

                  {/* Expanded Content */}
                  {expandedId === approval.id && (
                    <div className="px-4 pb-4 border-t border-slate-700/50">
                      {/* Details */}
                      <div className="mt-3 p-3 bg-slate-900/50 rounded-xl text-sm">
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <span className="text-slate-500">Archivo:</span>
                            <p className="text-slate-300 truncate">{approval.original_filename}</p>
                          </div>
                          <div>
                            <span className="text-slate-500">Destino:</span>
                            <p className="text-slate-300">{approval.suggested_cajon || '—'}</p>
                          </div>
                        </div>
                        {approval.sender_email && (
                          <p className="mt-2 text-xs text-slate-500">
                            De: {approval.sender_email}
                          </p>
                        )}
                      </div>

                      {/* Preview button */}
                      {approval.preview_url && (
                        <a
                          href={approval.preview_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-3 flex items-center justify-center gap-2 w-full py-2.5 bg-slate-700 text-slate-300 rounded-xl text-sm"
                        >
                          <Eye size={16} />
                          Ver documento
                        </a>
                      )}

                      {/* Action buttons */}
                      <div className="mt-3 flex gap-2">
                        <button
                          onClick={() => handleReject(approval)}
                          disabled={processingId === approval.id}
                          className="flex-1 flex items-center justify-center gap-2 py-3 bg-red-500/20 text-red-400 rounded-xl font-semibold disabled:opacity-50"
                        >
                          <X size={18} />
                          Rechazar
                        </button>
                        <button
                          onClick={() => handleApprove(approval)}
                          disabled={processingId === approval.id}
                          className="flex-1 flex items-center justify-center gap-2 py-3 bg-emerald-500 text-white rounded-xl font-semibold disabled:opacity-50"
                        >
                          {processingId === approval.id ? (
                            <RefreshCw size={18} className="animate-spin" />
                          ) : (
                            <Check size={18} />
                          )}
                          Aprobar
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )
        ) : (
          /* Values Tab */
          extractions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-20 h-20 bg-slate-800 rounded-full flex items-center justify-center mb-4">
                <Calculator size={36} className="text-slate-500" />
              </div>
              <h2 className="text-xl font-semibold text-slate-300">Sin valores pendientes</h2>
              <p className="text-sm text-slate-500 mt-2 max-w-xs">
                Cuando apruebes un documento, los valores detectados aparecerán aquí
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-slate-400 mb-4">
                {extractions.length} valor{extractions.length !== 1 ? 'es' : ''} pendiente{extractions.length !== 1 ? 's' : ''} de aprobar
              </p>
              
              {extractions.map((extraction) => (
                <div
                  key={extraction.document_id}
                  className="bg-slate-800/50 border border-slate-700 rounded-2xl overflow-hidden"
                >
                  {/* Card Header - Always visible */}
                  <button
                    onClick={() => setExpandedId(expandedId === extraction.document_id ? null : extraction.document_id)}
                    className="w-full p-4 flex items-center gap-3 text-left"
                  >
                    <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                      <DollarSign size={24} className="text-emerald-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-white">
                        {extraction.extracted_data.valor_total?.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' }) || '—'}
                      </h3>
                      <div className="flex items-center gap-2 text-sm text-slate-400 mt-0.5">
                        <span className="truncate">{extraction.extracted_data.concepto_detectado || extraction.document_name}</span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className="text-xs text-emerald-400">→ {getEstudioLabel(extraction.mapped_estudio_key)}</span>
                      {expandedId === extraction.document_id ? (
                        <ChevronUp size={16} className="text-slate-500" />
                      ) : (
                        <ChevronDown size={16} className="text-slate-500" />
                      )}
                    </div>
                  </button>

                  {/* Expanded Content */}
                  {expandedId === extraction.document_id && (
                    <div className="px-4 pb-4 border-t border-slate-700/50">
                      {/* Details */}
                      <div className="mt-3 p-3 bg-slate-900/50 rounded-xl text-sm space-y-2">
                        <div className="flex items-center gap-2">
                          <Building2 size={14} className="text-slate-500" />
                          <span className="text-slate-300">{extraction.property_name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <FileText size={14} className="text-slate-500" />
                          <span className="text-slate-300 truncate">{extraction.original_filename}</span>
                        </div>
                        {extraction.extracted_data.proveedor && (
                          <div className="flex items-center gap-2">
                            <span className="text-slate-500">Proveedor:</span>
                            <span className="text-slate-300">{extraction.extracted_data.proveedor}</span>
                          </div>
                        )}
                        <div className="flex items-center gap-2">
                          <span className="text-slate-500">Destino Excel:</span>
                          <span className="text-emerald-400 font-medium">{getEstudioLabel(extraction.mapped_estudio_key)} (Real)</span>
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="mt-3 flex gap-2">
                        <button
                          onClick={() => handleRejectExtraction(extraction)}
                          disabled={processingId === extraction.document_id}
                          className="flex-1 flex items-center justify-center gap-2 py-3 bg-red-500/20 text-red-400 rounded-xl font-semibold disabled:opacity-50"
                        >
                          <X size={18} />
                          No añadir
                        </button>
                        <button
                          onClick={() => handleApproveExtraction(extraction)}
                          disabled={processingId === extraction.document_id}
                          className="flex-1 flex items-center justify-center gap-2 py-3 bg-emerald-500 text-white rounded-xl font-semibold disabled:opacity-50"
                        >
                          {processingId === extraction.document_id ? (
                            <RefreshCw size={18} className="animate-spin" />
                          ) : (
                            <Check size={18} />
                          )}
                          Añadir al Excel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )
        )}
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-slate-900 to-transparent">
        <p className="text-center text-xs text-slate-600">
          Aboka AI • Gestión de reformas
        </p>
      </footer>
    </div>
  );
}


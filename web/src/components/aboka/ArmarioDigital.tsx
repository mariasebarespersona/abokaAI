'use client';

import React, { useState, useEffect, useCallback, Component, ErrorInfo, ReactNode } from 'react';
import {
  FolderOpen,
  FileText,
  Upload,
  Download,
  CheckCircle,
  Clock,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Search,
  Filter,
  MoreVertical,
  Eye,
  Trash2,
  ExternalLink,
  Home,
  Hammer,
  Landmark,
  Receipt,
  Store,
  Flag,
  Mail,
  Send
} from 'lucide-react';

// Error Boundary to catch React rendering errors
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ArmarioErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ArmarioDigital] React Error Boundary caught error:', error);
    console.error('[ArmarioDigital] Error Info:', errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-full flex flex-col items-center justify-center p-8 text-center">
          <AlertCircle size={48} className="text-red-500 mb-4" />
          <h3 className="text-lg font-medium text-red-600">Error al renderizar</h3>
          <p className="text-sm text-slate-500 mt-2 max-w-md">
            {this.state.error?.message || 'Ha ocurrido un error inesperado'}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            className="mt-4 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
          >
            Recargar página
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

interface ArmarioDocument {
  id: string;
  cajon: string;
  subcajon: string;
  document_name: string;
  is_uploaded: boolean;
  is_required: boolean;
  storage_path: string | null;
  importe: number | null;
  fecha_documento: string | null;
  original_filename: string | null;
}

interface CajonSummary {
  cajon: string;
  total_docs: number;
  uploaded_docs: number;
  required_docs: number;
  required_uploaded: number;
  completion_percentage: number;
}

interface ArmarioDigitalProps {
  propertyId: string | null;
  propertyName?: string | null;
  onDocumentUploaded?: () => void;
}

// Cajón configuration with icons and colors
const CAJONES_CONFIG: Record<string, { icon: React.ElementType; color: string; bgColor: string; borderColor: string; label: string }> = {
  'COMPRA': { 
    icon: Home, 
    color: 'text-emerald-600', 
    bgColor: 'bg-emerald-50', 
    borderColor: 'border-emerald-200',
    label: 'Adquisición'
  },
  'REFORMA': { 
    icon: Hammer, 
    color: 'text-amber-600', 
    bgColor: 'bg-amber-50', 
    borderColor: 'border-amber-200',
    label: 'Transformación'
  },
  'FINANCIERO': { 
    icon: Landmark, 
    color: 'text-blue-600', 
    bgColor: 'bg-blue-50', 
    borderColor: 'border-blue-200',
    label: 'Financiación'
  },
  'GESTIONES': { 
    icon: Receipt, 
    color: 'text-purple-600', 
    bgColor: 'bg-purple-50', 
    borderColor: 'border-purple-200',
    label: 'Recurrentes'
  },
  'VENTA': { 
    icon: Store, 
    color: 'text-rose-600', 
    bgColor: 'bg-rose-50', 
    borderColor: 'border-rose-200',
    label: 'Comercialización'
  },
  'CIERRE': { 
    icon: Flag, 
    color: 'text-slate-600', 
    bgColor: 'bg-slate-50', 
    borderColor: 'border-slate-200',
    label: 'Resultado'
  }
};

const CAJON_ORDER = ['COMPRA', 'REFORMA', 'FINANCIERO', 'GESTIONES', 'VENTA', 'CIERRE'];

// Main export wrapped in Error Boundary
export function ArmarioDigital(props: ArmarioDigitalProps) {
  return (
    <ArmarioErrorBoundary>
      <ArmarioDigitalContent {...props} />
    </ArmarioErrorBoundary>
  );
}

// Extraction proposal type
interface ExtractionProposal {
  documentId: string;
  documentName: string;
  originalFilename: string;
  concepto: string;
  valor: number;
  mappedKey: string;
  confidence: number;
}

// Internal component with all the logic
function ArmarioDigitalContent({ propertyId, propertyName, onDocumentUploaded }: ArmarioDigitalProps) {
  const [documents, setDocuments] = useState<ArmarioDocument[]>([]);
  const [summary, setSummary] = useState<CajonSummary[]>([]);
  const [expandedCajones, setExpandedCajones] = useState<Set<string>>(new Set(['COMPRA']));
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'uploaded' | 'pending' | 'required'>('all');
  const [uploadingDocId, setUploadingDocId] = useState<string | null>(null);
  
  // Extraction proposal modal state
  const [extractionProposal, setExtractionProposal] = useState<ExtractionProposal | null>(null);
  const [isApproving, setIsApproving] = useState(false);
  
  // Email modal state
  const [emailModalDoc, setEmailModalDoc] = useState<ArmarioDocument | null>(null);
  const [emailAddress, setEmailAddress] = useState('');
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  
  // Track if component is mounted to prevent state updates after unmount
  const isMountedRef = React.useRef(true);
  
  // Ref for the hidden file input and current document being uploaded
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const pendingDocRef = React.useRef<ArmarioDocument | null>(null);
  
  React.useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);
  
  // Handle file input click - store the target document
  const handleUploadClick = (doc: ArmarioDocument) => {
    console.log('[ArmarioDigital] handleUploadClick called for doc:', doc.document_name, 'propertyId:', propertyId);
    pendingDocRef.current = doc;
    
    // Force a small delay to ensure ref is ready after any re-renders
    setTimeout(() => {
      if (fileInputRef.current) {
        console.log('[ArmarioDigital] Clicking file input');
        fileInputRef.current.click();
      } else {
        console.error('[ArmarioDigital] fileInputRef.current is null!');
      }
    }, 10);
  };
  
  // Handle file selection from the hidden input
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    const doc = pendingDocRef.current;
    
    if (file && doc) {
      handleFileUpload(doc, file);
    }
    
    // Reset the input so the same file can be selected again
    e.target.value = '';
    pendingDocRef.current = null;
  };

  const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080';

  // Fetch armario data
  const fetchArmarioData = useCallback(async () => {
    if (!propertyId) return;
    
    // Only update state if component is mounted
    if (!isMountedRef.current) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('[ArmarioDigital] Fetching data for property:', propertyId);
      
      // Fetch documents list
      const docsRes = await fetch(`${BACKEND_URL}/api/armario/documents?property_id=${propertyId}`);
      
      // Check if still mounted before updating state
      if (!isMountedRef.current) return;
      
      if (!docsRes.ok) {
        throw new Error(`HTTP error fetching documents: ${docsRes.status}`);
      }
      
      const docsJson = await docsRes.json();
      
      // Check if still mounted before updating state
      if (!isMountedRef.current) return;
      
      if (docsJson.ok) {
        // Ensure documents is always an array
        const docs = Array.isArray(docsJson.documents) ? docsJson.documents : [];
        setDocuments(docs);
        console.log('[ArmarioDigital] Loaded', docs.length, 'documents');
      } else {
        throw new Error(docsJson.error || 'Error fetching documents');
      }
      
      // Fetch summary
      const summaryRes = await fetch(`${BACKEND_URL}/api/armario/summary?property_id=${propertyId}`);
      
      // Check if still mounted before updating state
      if (!isMountedRef.current) return;
      
      if (summaryRes.ok) {
        const summaryJson = await summaryRes.json();
        if (summaryJson.ok && isMountedRef.current) {
          const summaryData = Array.isArray(summaryJson.summary) ? summaryJson.summary : [];
          setSummary(summaryData);
        }
      }
      
    } catch (err: any) {
      console.error('[ArmarioDigital] Fetch error:', err);
      if (isMountedRef.current) {
        setError(err.message || 'Error al cargar el armario');
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [propertyId, BACKEND_URL]);

  useEffect(() => {
    fetchArmarioData();
  }, [fetchArmarioData]);

  // Toggle cajón expansion
  const toggleCajon = (cajon: string) => {
    setExpandedCajones(prev => {
      const next = new Set(prev);
      if (next.has(cajon)) {
        next.delete(cajon);
      } else {
        next.add(cajon);
      }
      return next;
    });
  };

  // Group documents by cajon and subcajon
  const groupedDocuments = React.useMemo(() => {
    // Safety check: ensure documents is an array
    if (!Array.isArray(documents)) {
      console.warn('[ArmarioDigital] documents is not an array:', documents);
      return {};
    }
    
    const filtered = documents.filter(doc => {
      // Safety check for document properties
      if (!doc || !doc.document_name || !doc.subcajon || !doc.cajon) {
        console.warn('[ArmarioDigital] Invalid document:', doc);
        return false;
      }
      
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const docName = (doc.document_name || '').toLowerCase();
        const subCajon = (doc.subcajon || '').toLowerCase();
        if (!docName.includes(query) && !subCajon.includes(query)) {
          return false;
        }
      }
      
      // Status filter
      if (filterStatus === 'uploaded' && !doc.is_uploaded) return false;
      if (filterStatus === 'pending' && doc.is_uploaded) return false;
      if (filterStatus === 'required' && !doc.is_required) return false;
      
      return true;
    });
    
    const grouped: Record<string, Record<string, ArmarioDocument[]>> = {};
    
    for (const doc of filtered) {
      if (!grouped[doc.cajon]) {
        grouped[doc.cajon] = {};
      }
      if (!grouped[doc.cajon][doc.subcajon]) {
        grouped[doc.cajon][doc.subcajon] = [];
      }
      grouped[doc.cajon][doc.subcajon].push(doc);
    }
    
    return grouped;
  }, [documents, searchQuery, filterStatus]);

  // Get summary for a specific cajon
  const getCajonSummary = (cajon: string): CajonSummary | undefined => {
    return summary.find(s => s.cajon === cajon);
  };

  // Calculate overall progress
  const overallProgress = React.useMemo(() => {
    const totalRequired = summary.reduce((acc, s) => acc + s.required_docs, 0);
    const totalUploaded = summary.reduce((acc, s) => acc + s.required_uploaded, 0);
    return totalRequired > 0 ? Math.round((totalUploaded / totalRequired) * 100) : 0;
  }, [summary]);

  // Handle file upload for a specific document slot
  const handleFileUpload = async (doc: ArmarioDocument, file: File) => {
    if (!propertyId || !isMountedRef.current) return;
    
    setUploadingDocId(doc.id);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append('property_id', propertyId);
      formData.append('cajon', doc.cajon);
      formData.append('subcajon', doc.subcajon);
      formData.append('document_name', doc.document_name);
      formData.append('file', file);
      
      console.log('[ArmarioDigital] Uploading file:', file.name, 'to', doc.cajon, doc.subcajon);
      
      const res = await fetch(`${BACKEND_URL}/api/armario/upload`, {
        method: 'POST',
        body: formData
      });
      
      // Check if still mounted
      if (!isMountedRef.current) return;
      
      if (!res.ok) {
        throw new Error(`HTTP error: ${res.status} ${res.statusText}`);
      }
      
      const json = await res.json();
      console.log('[ArmarioDigital] Upload response:', json);
      
      // Check if still mounted before state updates
      if (!isMountedRef.current) return;
      
      if (json.ok) {
        // Refresh data after successful upload
        console.log('[ArmarioDigital] Upload successful, refreshing data...');
        await fetchArmarioData();
        
        // Notify parent if callback exists (only if still mounted)
        if (isMountedRef.current && onDocumentUploaded) {
          try {
            console.log('[ArmarioDigital] Calling onDocumentUploaded callback...');
            onDocumentUploaded();
            console.log('[ArmarioDigital] onDocumentUploaded callback completed');
          } catch (callbackErr) {
            console.warn('[ArmarioDigital] onDocumentUploaded callback error:', callbackErr);
          }
        } else {
          console.log('[ArmarioDigital] onDocumentUploaded callback NOT called:', {
            isMounted: isMountedRef.current,
            hasCallback: !!onDocumentUploaded
          });
        }
        
        // Show extraction proposal modal if extraction was successful
        if (json.extraction?.success && json.extraction?.status === 'pending_approval') {
          console.log('[ArmarioDigital] Extraction result:', json.extraction);
          
          // Show the proposal modal
          if (isMountedRef.current) {
            setExtractionProposal({
              documentId: json.document_id,
              documentName: doc.document_name,
              originalFilename: file.name,
              concepto: json.extraction.concepto,
              valor: json.extraction.valor,
              mappedKey: json.extraction.mapped_key,
              confidence: json.extraction.confidence
            });
          }
        }
      } else {
        throw new Error(json.error || 'Error uploading file');
      }
      
    } catch (err: any) {
      console.error('[ArmarioDigital] Upload error:', err);
      if (isMountedRef.current) {
        setError(err.message || 'Error al subir el archivo');
      }
    } finally {
      if (isMountedRef.current) {
        setUploadingDocId(null);
      }
    }
  };

  // Handle document download
  const handleDownload = async (doc: ArmarioDocument) => {
    if (!propertyId || !doc.storage_path) return;
    
    try {
      const res = await fetch(
        `${BACKEND_URL}/api/armario/download?property_id=${propertyId}&cajon=${doc.cajon}&subcajon=${doc.subcajon}&document_name=${encodeURIComponent(doc.document_name)}`
      );
      
      const json = await res.json();
      
      if (json.url) {
        window.open(json.url, '_blank');
      } else {
        throw new Error(json.error || 'Could not get download URL');
      }
      
    } catch (err: any) {
      setError(err.message || 'Error al descargar');
    }
  };

  // Handle document deletion
  // IMPORTANT: This only deletes the document from THIS specific property
  // The property_id is ALWAYS included to ensure we never delete across properties
  const handleDeleteDocument = async (doc: ArmarioDocument) => {
    if (!propertyId || !isMountedRef.current) return;
    
    // Confirm before deleting
    const confirmed = window.confirm(
      `¿Estás seguro de que quieres eliminar "${doc.document_name}"?\n\nEsta acción no se puede deshacer.`
    );
    
    if (!confirmed) return;
    
    try {
      const res = await fetch(`${BACKEND_URL}/api/armario/delete`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          property_id: propertyId,  // CRITICAL: Always include property_id
          document_id: doc.id,
          cajon: doc.cajon,
          subcajon: doc.subcajon,
          document_name: doc.document_name
        })
      });
      
      // Check if still mounted
      if (!isMountedRef.current) return;
      
      const json = await res.json();
      
      if (json.ok) {
        // Refresh data after deletion
        await fetchArmarioData();
      } else {
        throw new Error(json.error || 'Error deleting document');
      }
      
    } catch (err: any) {
      if (isMountedRef.current) {
        setError(err.message || 'Error al eliminar el documento');
      }
    }
  };

  // Handle sending document by email
  const handleSendEmail = async () => {
    if (!emailModalDoc || !propertyId || !emailAddress || !isMountedRef.current) return;
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(emailAddress)) {
      setError('Por favor, introduce un email válido');
      return;
    }
    
    setIsSendingEmail(true);
    
    try {
      const res = await fetch(`${BACKEND_URL}/api/armario/send-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          property_id: propertyId,
          document_id: emailModalDoc.id,
          cajon: emailModalDoc.cajon,
          subcajon: emailModalDoc.subcajon,
          document_name: emailModalDoc.document_name,
          to_email: emailAddress,
          property_name: propertyName || 'Propiedad'
        })
      });
      
      if (!isMountedRef.current) return;
      
      const json = await res.json();
      
      if (json.ok) {
        // Success - close modal
        setEmailModalDoc(null);
        setEmailAddress('');
        alert(`✅ Documento enviado correctamente a ${emailAddress}`);
      } else {
        throw new Error(json.error || 'Error al enviar el email');
      }
      
    } catch (err: any) {
      if (isMountedRef.current) {
        setError(err.message || 'Error al enviar el documento por email');
      }
    } finally {
      if (isMountedRef.current) {
        setIsSendingEmail(false);
      }
    }
  };

  // Handle extraction approval - adds extracted value to Excel "Real" column
  const handleApproveExtraction = async () => {
    if (!extractionProposal || !propertyId || !isMountedRef.current) return;
    
    setIsApproving(true);
    
    try {
      const res = await fetch(`${BACKEND_URL}/api/armario/approve-extraction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: extractionProposal.documentId,
          property_id: propertyId
        })
      });
      
      if (!isMountedRef.current) return;
      
      const json = await res.json();
      
      if (json.ok) {
        console.log('[ArmarioDigital] Extraction approved:', json);
        setExtractionProposal(null);
        
        // Notify parent to refresh Excel
        if (onDocumentUploaded) {
          onDocumentUploaded();
        }
      } else {
        throw new Error(json.error || 'Error al aprobar la extracción');
      }
      
    } catch (err: any) {
      console.error('[ArmarioDigital] Approve extraction error:', err);
      if (isMountedRef.current) {
        setError(err.message || 'Error al aprobar la extracción');
      }
    } finally {
      if (isMountedRef.current) {
        setIsApproving(false);
      }
    }
  };

  // Handle extraction rejection - dismiss the proposal without updating Excel
  const handleRejectExtraction = async () => {
    if (!extractionProposal || !propertyId || !isMountedRef.current) return;
    
    try {
      const res = await fetch(`${BACKEND_URL}/api/armario/reject-extraction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: extractionProposal.documentId,
          property_id: propertyId
        })
      });
      
      if (!isMountedRef.current) return;
      
      const json = await res.json();
      
      if (json.ok) {
        console.log('[ArmarioDigital] Extraction rejected');
      }
      
    } catch (err: any) {
      console.error('[ArmarioDigital] Reject extraction error:', err);
    } finally {
      if (isMountedRef.current) {
        setExtractionProposal(null);
      }
    }
  };

  // Initialize armario for existing property
  const handleInitializeArmario = async () => {
    if (!propertyId || !isMountedRef.current) return;
    
    setIsLoading(true);
    
    try {
      const res = await fetch(`${BACKEND_URL}/api/armario/seed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ property_id: propertyId })
      });
      
      // Check if still mounted
      if (!isMountedRef.current) return;
      
      const json = await res.json();
      
      if (json.ok) {
        await fetchArmarioData();
      } else {
        throw new Error(json.error || 'Error initializing armario');
      }
      
    } catch (err: any) {
      if (isMountedRef.current) {
        setError(err.message || 'Error al inicializar el armario');
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  };

  // Render document row
  const renderDocument = (doc: ArmarioDocument) => {
    // Safety check
    if (!doc || !doc.id) {
      console.warn('[ArmarioDigital] Invalid document in renderDocument:', doc);
      return null;
    }
    
    const isUploading = uploadingDocId === doc.id;
    
    return (
      <div
        key={doc.id}
        className={`group flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all hover:bg-slate-50 ${
          doc.is_uploaded ? 'bg-emerald-50/50' : ''
        }`}
      >
        {/* Status Icon */}
        <div className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center ${
          doc.is_uploaded 
            ? 'bg-emerald-100 text-emerald-600' 
            : doc.is_required 
              ? 'bg-amber-100 text-amber-600'
              : 'bg-slate-100 text-slate-400'
        }`}>
          {isUploading ? (
            <RefreshCw size={14} className="animate-spin" />
          ) : doc.is_uploaded ? (
            <CheckCircle size={14} />
          ) : doc.is_required ? (
            <AlertCircle size={14} />
          ) : (
            <Clock size={14} />
          )}
        </div>
        
        {/* Document Info */}
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-medium truncate ${
            doc.is_uploaded ? 'text-slate-700' : 'text-slate-500'
          }`}>
            {doc.document_name}
          </p>
          {doc.original_filename && (
            <p className="text-[10px] text-slate-400 truncate">
              {doc.original_filename}
            </p>
          )}
          {doc.importe != null && typeof doc.importe === 'number' && (
            <p className="text-xs text-emerald-600 font-medium">
              {doc.importe.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
            </p>
          )}
        </div>
        
        {/* Required Badge */}
        {doc.is_required && !doc.is_uploaded && (
          <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-100 text-amber-700 rounded-full">
            Obligatorio
          </span>
        )}
        
        {/* Actions - Always visible */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {doc.is_uploaded ? (
            <>
              <button
                onClick={() => handleDownload(doc)}
                className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-500 hover:text-slate-700 transition-colors"
                title="Descargar"
              >
                <Download size={14} />
              </button>
              <button
                className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-500 hover:text-slate-700 transition-colors"
                title="Ver"
              >
                <Eye size={14} />
              </button>
              <button
                onClick={() => setEmailModalDoc(doc)}
                className="p-1.5 rounded-lg hover:bg-blue-100 text-slate-400 hover:text-blue-600 transition-colors"
                title="Enviar por email"
              >
                <Mail size={14} />
              </button>
              <button
                onClick={() => handleDeleteDocument(doc)}
                className="p-1.5 rounded-lg hover:bg-red-100 text-slate-400 hover:text-red-600 transition-colors"
                title="Eliminar documento"
              >
                <Trash2 size={14} />
              </button>
            </>
          ) : (
            <button
              onClick={() => handleUploadClick(doc)}
              disabled={isUploading || uploadingDocId !== null}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploading ? (
                <RefreshCw size={12} className="animate-spin" />
              ) : (
                <Upload size={12} />
              )}
              {isUploading ? 'Subiendo...' : 'Subir'}
            </button>
          )}
        </div>
      </div>
    );
  };

  // Hidden file input - ALWAYS render this at the top level, regardless of state
  // This ensures the ref is always available when user clicks "Subir"
  const fileInputElement = (
    <input
      ref={fileInputRef}
      type="file"
      className="hidden"
      accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.webp,.xlsx,.xls"
      onChange={handleFileInputChange}
    />
  );

  // No property selected state
  if (!propertyId) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-400 p-8">
        {fileInputElement}
        <FolderOpen size={48} className="mb-4 opacity-30" />
        <h3 className="text-lg font-medium text-slate-500">Armario Digital</h3>
        <p className="text-sm text-center mt-2">
          Selecciona una propiedad para ver su documentación
        </p>
      </div>
    );
  }

  // Loading state
  if (isLoading && documents.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center">
        {fileInputElement}
        <RefreshCw size={32} className="animate-spin text-blue-500 mb-4" />
        <p className="text-sm text-slate-500">Cargando armario digital...</p>
      </div>
    );
  }

  // Empty state - need to initialize
  if (documents.length === 0 && !isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8">
        {fileInputElement}
        <FolderOpen size={48} className="mb-4 text-slate-300" />
        <h3 className="text-lg font-medium text-slate-600">Armario vacío</h3>
        <p className="text-sm text-slate-400 text-center mt-2 mb-6">
          Esta propiedad no tiene el armario digital inicializado
        </p>
        <button
          onClick={handleInitializeArmario}
          disabled={isLoading}
          className="px-4 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 transition-colors shadow-lg shadow-blue-500/25 flex items-center gap-2"
        >
          <FolderOpen size={16} />
          Inicializar Armario
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white rounded-xl border border-slate-200 overflow-hidden">
      {/* Hidden file input */}
      {fileInputElement}
      
      {/* Extraction Proposal Modal */}
      {extractionProposal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-emerald-500 to-teal-600 px-6 py-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                  <FileText size={20} className="text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Valor Detectado</h3>
                  <p className="text-emerald-100 text-sm">Extracción automática</p>
                </div>
              </div>
            </div>
            
            {/* Content */}
            <div className="p-6">
              <div className="space-y-4">
                <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
                  <FileText size={18} className="text-slate-400 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-slate-700">Documento</p>
                    <p className="text-sm text-slate-500">{extractionProposal.originalFilename}</p>
                  </div>
                </div>
                
                <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
                  <Receipt size={18} className="text-slate-400 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-slate-700">Concepto detectado</p>
                    <p className="text-sm text-slate-500">{extractionProposal.concepto}</p>
                  </div>
                </div>
                
                <div className="flex items-start gap-3 p-4 bg-emerald-50 rounded-lg border border-emerald-200">
                  <Landmark size={20} className="text-emerald-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-emerald-800">Importe Total</p>
                    <p className="text-2xl font-bold text-emerald-600">
                      {extractionProposal.valor.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                    </p>
                  </div>
                </div>
                
                <div className={`p-3 rounded-lg border ${extractionProposal.confidence >= 0.5 ? 'bg-blue-50 border-blue-200' : 'bg-amber-50 border-amber-200'}`}>
                  <p className={`text-sm ${extractionProposal.confidence >= 0.5 ? 'text-blue-800' : 'text-amber-800'}`}>
                    <span className="font-medium">Se añadirá a:</span> {extractionProposal.mappedKey?.replace(/_/g, ' → ').replace('compra', 'COMPRA').replace('reforma', 'REFORMA').replace('financiero', 'FINANCIERO').replace('gestiones', 'GESTIONES') || 'Categoría no detectada'}
                  </p>
                  <p className={`text-xs mt-1 ${extractionProposal.confidence >= 0.5 ? 'text-blue-600' : 'text-amber-600'}`}>
                    Columna: <span className="font-medium">Real</span> • Confianza: {Math.round((extractionProposal.confidence || 0) * 100)}%
                    {extractionProposal.confidence < 0.5 && <span className="ml-2">⚠️ Verifica la categoría</span>}
                  </p>
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex gap-3 mt-6">
                <button
                  onClick={handleRejectExtraction}
                  disabled={isApproving}
                  className="flex-1 px-4 py-2.5 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors font-medium disabled:opacity-50"
                >
                  Rechazar
                </button>
                <button
                  onClick={handleApproveExtraction}
                  disabled={isApproving}
                  className="flex-1 px-4 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isApproving ? (
                    <>
                      <RefreshCw size={16} className="animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <CheckCircle size={16} />
                      Añadir al Excel
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Email Modal */}
      {emailModalDoc && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-500 to-indigo-600 px-6 py-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                  <Mail size={20} className="text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Enviar por Email</h3>
                  <p className="text-blue-100 text-sm truncate max-w-[250px]">{emailModalDoc.document_name}</p>
                </div>
              </div>
            </div>
            
            {/* Content */}
            <div className="p-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Dirección de email
                  </label>
                  <input
                    type="email"
                    value={emailAddress}
                    onChange={(e) => setEmailAddress(e.target.value)}
                    placeholder="ejemplo@email.com"
                    className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                    autoFocus
                  />
                </div>
                
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-sm text-slate-600">
                    <span className="font-medium">Documento:</span> {emailModalDoc.original_filename || emailModalDoc.document_name}
                  </p>
                  <p className="text-sm text-slate-600">
                    <span className="font-medium">Propiedad:</span> {propertyName || 'Sin nombre'}
                  </p>
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => {
                    setEmailModalDoc(null);
                    setEmailAddress('');
                  }}
                  disabled={isSendingEmail}
                  className="flex-1 px-4 py-2.5 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors font-medium disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSendEmail}
                  disabled={isSendingEmail || !emailAddress}
                  className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isSendingEmail ? (
                    <>
                      <RefreshCw size={16} className="animate-spin" />
                      Enviando...
                    </>
                  ) : (
                    <>
                      <Send size={16} />
                      Enviar
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <FolderOpen size={20} className="text-white" />
            </div>
            <div>
              <h2 className="font-bold text-slate-800">Armario Digital</h2>
              <p className="text-xs text-slate-500">
                {summary.reduce((acc, s) => acc + s.uploaded_docs, 0)} de {summary.reduce((acc, s) => acc + s.total_docs, 0)} documentos
              </p>
            </div>
          </div>
          
          {/* Overall Progress */}
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-xs text-slate-500">Obligatorios</p>
              <p className="text-lg font-bold text-slate-800">{overallProgress}%</p>
            </div>
            <div className="w-16 h-16">
              <svg viewBox="0 0 36 36" className="transform -rotate-90">
                <circle
                  cx="18" cy="18" r="15"
                  fill="none"
                  stroke="#e2e8f0"
                  strokeWidth="3"
                />
                <circle
                  cx="18" cy="18" r="15"
                  fill="none"
                  stroke={overallProgress >= 80 ? '#10b981' : overallProgress >= 50 ? '#f59e0b' : '#ef4444'}
                  strokeWidth="3"
                  strokeDasharray={`${overallProgress} 100`}
                  strokeLinecap="round"
                />
              </svg>
            </div>
          </div>
        </div>
        
        {/* Search and Filters */}
        <div className="flex items-center gap-2 mt-3">
          <div className="flex-1 relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar documento..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm bg-slate-100 border-0 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
          </div>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as any)}
            className="px-3 py-2 text-sm bg-slate-100 border-0 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          >
            <option value="all">Todos</option>
            <option value="uploaded">Subidos</option>
            <option value="pending">Pendientes</option>
            <option value="required">Obligatorios</option>
          </select>
          <button
            onClick={fetchArmarioData}
            disabled={isLoading}
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 transition-colors"
            title="Actualizar"
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>
      
      {/* Error Banner */}
      {error && (
        <div className="mx-4 mt-3 px-4 py-2 bg-red-50 border border-red-100 rounded-lg flex items-center gap-2 text-sm text-red-600">
          <AlertCircle size={16} />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-600">
            ×
          </button>
        </div>
      )}
      
      {/* Cajones Accordion */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {CAJON_ORDER.map(cajon => {
          const config = CAJONES_CONFIG[cajon];
          const cajonSummary = getCajonSummary(cajon);
          const isExpanded = expandedCajones.has(cajon);
          const cajonDocs = groupedDocuments[cajon] || {};
          const subcajones = Object.keys(cajonDocs);
          const Icon = config.icon;
          
          // Skip if no documents match filter
          if (subcajones.length === 0 && searchQuery) return null;
          
          return (
            <div
              key={cajon}
              className={`rounded-xl border ${config.borderColor} overflow-hidden transition-all`}
            >
              {/* Cajón Header */}
              <button
                onClick={() => toggleCajon(cajon)}
                className={`w-full flex items-center gap-3 px-4 py-3 ${config.bgColor} hover:brightness-95 transition-all`}
              >
                {isExpanded ? (
                  <ChevronDown size={16} className={config.color} />
                ) : (
                  <ChevronRight size={16} className={config.color} />
                )}
                
                <div className={`w-8 h-8 rounded-lg ${config.bgColor} border ${config.borderColor} flex items-center justify-center`}>
                  <Icon size={16} className={config.color} />
                </div>
                
                <div className="flex-1 text-left">
                  <h3 className={`font-bold text-sm ${config.color}`}>{cajon}</h3>
                  <p className="text-[10px] text-slate-500">{config.label}</p>
                </div>
                
                {/* Progress Bar */}
                {cajonSummary && (
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          cajonSummary.completion_percentage >= 80 ? 'bg-emerald-500' :
                          cajonSummary.completion_percentage >= 50 ? 'bg-amber-500' : 'bg-rose-500'
                        }`}
                        style={{ width: `${cajonSummary.completion_percentage}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-slate-500 w-10 text-right">
                      {cajonSummary.uploaded_docs}/{cajonSummary.total_docs}
                    </span>
                  </div>
                )}
              </button>
              
              {/* Cajón Content */}
              {isExpanded && (
                <div className="px-3 pb-3 bg-white divide-y divide-slate-100">
                  {subcajones.length > 0 ? (
                    subcajones.map(subcajon => (
                      <div key={subcajon} className="py-2">
                        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-2">
                          {subcajon}
                        </h4>
                        <div className="space-y-1">
                          {cajonDocs[subcajon].map(doc => renderDocument(doc))}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="py-4 text-center text-sm text-slate-400">
                      No hay documentos que mostrar
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}


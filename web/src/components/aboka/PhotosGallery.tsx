'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Camera,
  Upload,
  Trash2,
  Star,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  ImageIcon,
  X,
  Check,
  AlertCircle,
  Home,
  Hammer,
  Flag
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface Photo {
  id: string;
  property_id: string;
  category: 'ANTES' | 'DURANTE' | 'DESPUES';
  storage_path: string;
  filename: string;
  original_filename: string | null;
  is_featured: boolean;
  description: string | null;
  uploaded_at: string;
  signed_url?: string;
}

interface PhotosSummary {
  ANTES: number;
  DURANTE: number;
  DESPUES: number;
  total: number;
}

interface PhotosGalleryProps {
  propertyId: string | null;
  propertyName?: string | null;
  onPhotoUploaded?: () => void;
}

// Category configuration
const CATEGORIES_CONFIG: Record<string, { icon: React.ElementType; color: string; bgColor: string; borderColor: string; label: string; description: string }> = {
  'ANTES': { 
    icon: Home, 
    color: 'text-slate-600', 
    bgColor: 'bg-slate-50', 
    borderColor: 'border-slate-200',
    label: 'Antes',
    description: 'Estado inicial de la propiedad'
  },
  'DURANTE': { 
    icon: Hammer, 
    color: 'text-amber-600', 
    bgColor: 'bg-amber-50', 
    borderColor: 'border-amber-200',
    label: 'Durante',
    description: 'Progreso de la reforma'
  },
  'DESPUES': { 
    icon: Flag, 
    color: 'text-emerald-600', 
    bgColor: 'bg-emerald-50', 
    borderColor: 'border-emerald-200',
    label: 'Después',
    description: 'Resultado final'
  }
};

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export function PhotosGallery({ propertyId, propertyName, onPhotoUploaded }: PhotosGalleryProps) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [summary, setSummary] = useState<PhotosSummary>({ ANTES: 0, DURANTE: 0, DESPUES: 0, total: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['ANTES', 'DURANTE', 'DESPUES']));
  const [uploadingCategory, setUploadingCategory] = useState<string | null>(null);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingCategoryRef = useRef<string | null>(null);
  
  const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080';

  // Fetch photos
  const fetchPhotos = useCallback(async (showLoading = true) => {
    if (!propertyId) {
      setIsLoading(false);
      return;
    }

    if (showLoading) setIsLoading(true);
    else setIsRefreshing(true);
    setError(null);

    try {
      // Fetch all photos
      const photosRes = await fetch(`${BACKEND_URL}/api/photos?property_id=${propertyId}`);
      const photosJson = await photosRes.json();
      
      if (photosJson.ok) {
        setPhotos(photosJson.photos || []);
      }

      // Fetch summary
      const summaryRes = await fetch(`${BACKEND_URL}/api/photos/summary?property_id=${propertyId}`);
      const summaryJson = await summaryRes.json();
      
      if (summaryJson.ok) {
        setSummary(summaryJson.summary);
      }
    } catch (err) {
      console.error('Error fetching photos:', err);
      setError('Error al cargar las fotos');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [propertyId, BACKEND_URL]);

  // Initial fetch
  useEffect(() => {
    fetchPhotos();
  }, [fetchPhotos]);

  // Toggle category expansion
  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(category)) {
        newSet.delete(category);
      } else {
        newSet.add(category);
      }
      return newSet;
    });
  };

  // Handle upload click
  const handleUploadClick = (category: string) => {
    pendingCategoryRef.current = category;
    fileInputRef.current?.click();
  };

  // Handle file selection
  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0 || !propertyId || !pendingCategoryRef.current) return;

    const category = pendingCategoryRef.current;
    setUploadingCategory(category);

    try {
      for (const file of Array.from(files)) {
        // Validate file type
        if (!file.type.startsWith('image/')) {
          setError('Solo se permiten archivos de imagen');
          continue;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('property_id', propertyId);
        formData.append('category', category);

        const response = await fetch(`${BACKEND_URL}/api/photos/upload`, {
          method: 'POST',
          body: formData,
        });

        const result = await response.json();

        if (!result.ok) {
          setError(result.error || 'Error al subir la foto');
        }
      }

      // Refresh photos
      await fetchPhotos(false);
      
      // Notify parent
      if (onPhotoUploaded) {
        onPhotoUploaded();
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError('Error al subir la foto');
    } finally {
      setUploadingCategory(null);
      pendingCategoryRef.current = null;
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Toggle featured status
  const handleToggleFeatured = async (photo: Photo) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/photos/${photo.id}/featured`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_featured: !photo.is_featured }),
      });

      const result = await response.json();

      if (result.ok) {
        // Update local state
        setPhotos(prev => prev.map(p => 
          p.id === photo.id ? { ...p, is_featured: !p.is_featured } : p
        ));
      }
    } catch (err) {
      console.error('Error toggling featured:', err);
    }
  };

  // Delete photo
  const handleDeletePhoto = async (photo: Photo) => {
    if (!confirm('¿Eliminar esta foto?')) return;

    try {
      const response = await fetch(
        `${BACKEND_URL}/api/photos/${photo.id}?property_id=${propertyId}`,
        { method: 'DELETE' }
      );

      const result = await response.json();

      if (result.ok) {
        setPhotos(prev => prev.filter(p => p.id !== photo.id));
        setSummary(prev => ({
          ...prev,
          [photo.category]: Math.max(0, prev[photo.category] - 1),
          total: Math.max(0, prev.total - 1)
        }));
        
        if (selectedPhoto?.id === photo.id) {
          setSelectedPhoto(null);
        }

        if (onPhotoUploaded) {
          onPhotoUploaded();
        }
      }
    } catch (err) {
      console.error('Error deleting photo:', err);
    }
  };

  // Get photos by category
  const getPhotosByCategory = (category: string) => {
    return photos.filter(p => p.category === category);
  };

  // No property selected
  if (!propertyId) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-400 p-8">
        <Camera size={48} className="mb-4 opacity-30" />
        <h3 className="text-lg font-medium text-slate-500">Galería de Fotos</h3>
        <p className="text-sm text-center mt-2">
          Selecciona una propiedad para ver sus fotos
        </p>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <p className="mt-4 text-sm text-slate-500">Cargando fotos...</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white rounded-xl border border-slate-200 overflow-hidden">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-violet-900 to-violet-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center">
              <Camera size={24} className="text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Galería de Fotos</h2>
              <p className="text-sm text-violet-200">
                {summary.total} foto{summary.total !== 1 ? 's' : ''} • {propertyName || 'Propiedad'}
              </p>
            </div>
          </div>
          <button
            onClick={() => fetchPhotos(false)}
            disabled={isRefreshing}
            className="p-2.5 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors disabled:opacity-50"
            title="Actualizar"
          >
            <RefreshCw size={18} className={isRefreshing ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
          <AlertCircle size={16} />
          <span className="text-sm">{error}</span>
          <button onClick={() => setError(null)} className="ml-auto">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Categories */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {(['ANTES', 'DURANTE', 'DESPUES'] as const).map((category) => {
          const config = CATEGORIES_CONFIG[category];
          const Icon = config.icon;
          const categoryPhotos = getPhotosByCategory(category);
          const isExpanded = expandedCategories.has(category);
          const isUploading = uploadingCategory === category;

          return (
            <div
              key={category}
              className={`rounded-xl border ${config.borderColor} overflow-hidden transition-all`}
            >
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(category)}
                className={`w-full flex items-center gap-3 px-4 py-3 ${config.bgColor} hover:bg-opacity-80 transition-colors`}
              >
                <div className={`w-10 h-10 rounded-lg ${config.bgColor} border ${config.borderColor} flex items-center justify-center`}>
                  <Icon size={20} className={config.color} />
                </div>
                <div className="flex-1 text-left">
                  <h3 className={`font-semibold ${config.color}`}>{config.label}</h3>
                  <p className="text-xs text-slate-500">{config.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-medium ${config.color} px-2.5 py-1 rounded-full ${config.bgColor}`}>
                    {summary[category]} foto{summary[category] !== 1 ? 's' : ''}
                  </span>
                  {isExpanded ? (
                    <ChevronDown size={18} className="text-slate-400" />
                  ) : (
                    <ChevronRight size={18} className="text-slate-400" />
                  )}
                </div>
              </button>

              {/* Category Content */}
              {isExpanded && (
                <div className="p-4 bg-white">
                  {/* Upload Button */}
                  <button
                    onClick={() => handleUploadClick(category)}
                    disabled={isUploading}
                    className={`w-full mb-4 flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed ${config.borderColor} rounded-lg text-sm font-medium ${config.color} hover:${config.bgColor} transition-colors disabled:opacity-50`}
                  >
                    {isUploading ? (
                      <>
                        <RefreshCw size={16} className="animate-spin" />
                        Subiendo...
                      </>
                    ) : (
                      <>
                        <Upload size={16} />
                        Subir fotos a {config.label}
                      </>
                    )}
                  </button>

                  {/* Photos Grid */}
                  {categoryPhotos.length > 0 ? (
                    <div className="grid grid-cols-3 gap-3">
                      {categoryPhotos.map((photo) => (
                        <div
                          key={photo.id}
                          className="relative group aspect-square rounded-lg overflow-hidden bg-slate-800 cursor-pointer"
                          onClick={() => setSelectedPhoto(photo)}
                        >
                          {photo.signed_url ? (
                            <img
                              src={photo.signed_url}
                              alt={photo.filename}
                              className="w-full h-full object-contain"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <ImageIcon size={24} className="text-slate-300" />
                            </div>
                          )}

                          {/* Featured badge */}
                          {photo.is_featured && (
                            <div className="absolute top-2 left-2 w-6 h-6 bg-amber-400 rounded-full flex items-center justify-center">
                              <Star size={12} className="text-white fill-white" />
                            </div>
                          )}

                          {/* Hover overlay */}
                          <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleToggleFeatured(photo);
                              }}
                              className={`p-2 rounded-full ${photo.is_featured ? 'bg-amber-400 text-white' : 'bg-white text-slate-700'} hover:scale-110 transition-transform`}
                              title={photo.is_featured ? 'Quitar destacado' : 'Marcar como destacada'}
                            >
                              <Star size={14} className={photo.is_featured ? 'fill-white' : ''} />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeletePhoto(photo);
                              }}
                              className="p-2 rounded-full bg-white text-red-600 hover:scale-110 transition-transform"
                              title="Eliminar"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-slate-400">
                      <ImageIcon size={32} className="mx-auto mb-2 opacity-30" />
                      <p className="text-sm">No hay fotos en esta categoría</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Photo Preview Modal */}
      {selectedPhoto && (
        <div
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedPhoto(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh] w-full">
            <button
              onClick={() => setSelectedPhoto(null)}
              className="absolute top-4 right-4 z-10 p-2 bg-white/10 hover:bg-white/20 rounded-full text-white"
            >
              <X size={24} />
            </button>
            
            <img
              src={selectedPhoto.signed_url}
              alt={selectedPhoto.filename}
              className="w-full h-full object-contain rounded-lg"
              onClick={(e) => e.stopPropagation()}
            />
            
            <div className="absolute bottom-4 left-4 right-4 bg-black/60 rounded-lg p-3 flex items-center justify-between">
              <div>
                <p className="text-white font-medium">{selectedPhoto.original_filename || selectedPhoto.filename}</p>
                <p className="text-white/70 text-sm">
                  {CATEGORIES_CONFIG[selectedPhoto.category]?.label} • 
                  {new Date(selectedPhoto.uploaded_at).toLocaleDateString('es-ES')}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleToggleFeatured(selectedPhoto);
                    setSelectedPhoto({ ...selectedPhoto, is_featured: !selectedPhoto.is_featured });
                  }}
                  className={`p-2 rounded-lg ${selectedPhoto.is_featured ? 'bg-amber-400 text-white' : 'bg-white/20 text-white'}`}
                >
                  <Star size={18} className={selectedPhoto.is_featured ? 'fill-white' : ''} />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeletePhoto(selectedPhoto);
                  }}
                  className="p-2 rounded-lg bg-red-500/80 text-white"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


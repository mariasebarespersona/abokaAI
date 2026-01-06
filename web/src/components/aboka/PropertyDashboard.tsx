'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Building2, FileText, Calculator, TrendingUp,
  CheckCircle, Clock, AlertTriangle, Euro,
  FolderOpen, BarChart3, PieChart, Target, RefreshCw
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface ArmarioSummary {
  cajon: string;
  total_docs: number;
  uploaded_docs: number;
  required_docs: number;
  required_uploaded: number;
}

interface EstudioSummary {
  totalGastos: number;
  totalIngresos: number;
  beneficioNeto: number;
  roi: number;
  completionPercent: number;
}

interface PropertyDashboardProps {
  propertyId: string | null;
  propertyName: string | null;
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export function PropertyDashboard({ propertyId, propertyName }: PropertyDashboardProps) {
  const [armarioSummary, setArmarioSummary] = useState<ArmarioSummary[]>([]);
  const [estudioSummary, setEstudioSummary] = useState<EstudioSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080';

  // Fetch dashboard data
  const fetchData = useCallback(async (showLoading = true) => {
    if (!propertyId) {
      setIsLoading(false);
      return;
    }

    if (showLoading) setIsLoading(true);
    else setIsRefreshing(true);
    setError(null);

    try {
      // Fetch Armario summary
        const armarioRes = await fetch(`${BACKEND_URL}/api/armario/summary?property_id=${propertyId}`);
        const armarioJson = await armarioRes.json();
        console.log('[PropertyDashboard] Armario summary response:', armarioJson);
        
        // Handle different response formats
        let summaryData: ArmarioSummary[] = [];
        if (Array.isArray(armarioJson)) {
          summaryData = armarioJson;
        } else if (armarioJson.summary && Array.isArray(armarioJson.summary)) {
          summaryData = armarioJson.summary;
        } else if (armarioJson.ok && armarioJson.data && Array.isArray(armarioJson.data)) {
          summaryData = armarioJson.data;
        }
        setArmarioSummary(summaryData);

        // Fetch Estudio Económico summary
        const estudioRes = await fetch(`${BACKEND_URL}/api/estudio/${propertyId}`);
        const estudioJson = await estudioRes.json();
        if (estudioJson.ok) {
          const items = estudioJson.items || [];
          
          // Calculate summary
          let totalGastos = 0;
          let totalIngresos = 0;
          let filledFields = 0;
          let totalFields = 0;

          items.forEach((item: any) => {
            // API returns: key, estimado, real, category
            if (item.key && !item.key.includes('_total')) {
              totalFields++;
              if (item.estimado || item.real) {
                filledFields++;
              }
              
              // Use estimado for summary, fallback to real if no estimate
              const value = item.estimado || item.real || 0;
              
              if (item.category === 'VENTA') {
                totalIngresos += value;
              } else {
                totalGastos += value;
              }
            }
          });

          const beneficioNeto = totalIngresos - totalGastos;
          const roi = totalGastos > 0 ? (beneficioNeto / totalGastos) * 100 : 0;

          setEstudioSummary({
            totalGastos,
            totalIngresos,
            beneficioNeto,
            roi,
            completionPercent: totalFields > 0 ? (filledFields / totalFields) * 100 : 0
          });
        }
      } catch (err) {
        console.error('Dashboard fetch error:', err);
        setError('Error al cargar los datos');
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
  }, [propertyId, BACKEND_URL]);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Manual refresh handler
  const handleRefresh = () => {
    fetchData(false);
  };

  // Calculate totals from armario summary (with safety check)
  const armarioTotals = (Array.isArray(armarioSummary) ? armarioSummary : []).reduce(
    (acc, item) => ({
      total: acc.total + (item.total_docs || 0),
      uploaded: acc.uploaded + (item.uploaded_docs || 0),
      required: acc.required + (item.required_docs || 0),
      requiredUploaded: acc.requiredUploaded + (item.required_uploaded || 0),
    }),
    { total: 0, uploaded: 0, required: 0, requiredUploaded: 0 }
  );

  const docCompletionPercent = armarioTotals.required > 0
    ? (armarioTotals.requiredUploaded / armarioTotals.required) * 100
    : 0;

  // Format currency
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0
    }).format(val);
  };

  // No property selected
  if (!propertyId) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-400 p-8">
        <Building2 size={48} className="mb-4 opacity-30" />
        <h3 className="text-lg font-medium text-slate-500">Dashboard</h3>
        <p className="text-sm text-center mt-2">
          Selecciona una propiedad para ver su resumen
        </p>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <p className="mt-4 text-sm text-slate-500">Cargando dashboard...</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white rounded-xl border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-slate-900 to-slate-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center">
              <BarChart3 size={24} className="text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">{propertyName || 'Propiedad'}</h2>
              <p className="text-sm text-slate-300">Resumen del estado actual</p>
            </div>
          </div>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="p-2.5 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors disabled:opacity-50"
            title="Actualizar datos"
          >
            <RefreshCw size={18} className={isRefreshing ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Main Metrics Grid */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {/* Documents Progress */}
          <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-xl p-5 border border-indigo-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-indigo-500 flex items-center justify-center">
                <FolderOpen size={20} className="text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-indigo-900">Documentación</h3>
                <p className="text-xs text-indigo-600">Armario Digital</p>
              </div>
            </div>
            <div className="mb-2">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-indigo-700">Documentos subidos</span>
                <span className="font-bold text-indigo-900">{armarioTotals.uploaded} / {armarioTotals.total}</span>
              </div>
              <div className="h-3 bg-indigo-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-indigo-500 rounded-full transition-all"
                  style={{ width: `${armarioTotals.total > 0 ? (armarioTotals.uploaded / armarioTotals.total) * 100 : 0}%` }}
                />
              </div>
            </div>
            <p className="text-xs text-indigo-600">
              {armarioTotals.requiredUploaded} de {armarioTotals.required} obligatorios completados
            </p>
          </div>

          {/* Financial Progress */}
          <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-xl p-5 border border-emerald-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-emerald-500 flex items-center justify-center">
                <Calculator size={20} className="text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-emerald-900">Estudio Económico</h3>
                <p className="text-xs text-emerald-600">Completado</p>
              </div>
            </div>
            <div className="mb-2">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-emerald-700">Campos rellenados</span>
                <span className="font-bold text-emerald-900">{estudioSummary?.completionPercent.toFixed(0) || 0}%</span>
              </div>
              <div className="h-3 bg-emerald-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-emerald-500 rounded-full transition-all"
                  style={{ width: `${estudioSummary?.completionPercent || 0}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Financial Summary Cards */}
        <h3 className="font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <Euro size={16} />
          Resumen Financiero
        </h3>
        <div className="grid grid-cols-4 gap-3 mb-6">
          <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
            <p className="text-xs text-slate-500 mb-1">Total Gastos</p>
            <p className="text-lg font-bold text-red-600 font-mono">
              {formatCurrency(estudioSummary?.totalGastos || 0)}
            </p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
            <p className="text-xs text-slate-500 mb-1">Ingresos Est.</p>
            <p className="text-lg font-bold text-emerald-600 font-mono">
              {formatCurrency(estudioSummary?.totalIngresos || 0)}
            </p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
            <p className="text-xs text-slate-500 mb-1">Beneficio Neto</p>
            <p className={`text-lg font-bold font-mono ${(estudioSummary?.beneficioNeto || 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {formatCurrency(estudioSummary?.beneficioNeto || 0)}
            </p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
            <p className="text-xs text-slate-500 mb-1">ROI Estimado</p>
            <p className={`text-lg font-bold font-mono ${(estudioSummary?.roi || 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {(estudioSummary?.roi || 0).toFixed(1)}%
            </p>
          </div>
        </div>

        {/* Documents by Category */}
        <h3 className="font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <PieChart size={16} />
          Documentos por Categoría
        </h3>
        <div className="grid grid-cols-3 gap-3">
          {(Array.isArray(armarioSummary) ? armarioSummary : []).map((category) => {
            // Calculate percentage based on uploaded docs vs total
            const uploadPercent = category.total_docs > 0
              ? (category.uploaded_docs / category.total_docs) * 100
              : 0;
            
            const hasUploads = category.uploaded_docs > 0;
            const colorClass = uploadPercent === 100 
              ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
              : hasUploads 
                ? 'bg-blue-50 border-blue-200 text-blue-700'
                : 'bg-slate-50 border-slate-200 text-slate-600';

            return (
              <div 
                key={category.cajon}
                className={`rounded-lg p-3 border ${colorClass}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-sm">{category.cajon}</span>
                  {uploadPercent === 100 ? (
                    <CheckCircle size={16} className="text-emerald-500" />
                  ) : hasUploads ? (
                    <FileText size={16} className="text-blue-500" />
                  ) : (
                    <Clock size={16} className="text-slate-400" />
                  )}
                </div>
                <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden mb-1">
                  <div 
                    className={`h-full rounded-full ${uploadPercent === 100 ? 'bg-emerald-500' : 'bg-blue-500'}`}
                    style={{ width: `${uploadPercent}%` }}
                  />
                </div>
                <p className="text-xs opacity-70">
                  {category.uploaded_docs}/{category.total_docs} docs
                  {category.required_docs > 0 && ` (${category.required_uploaded}/${category.required_docs} oblig.)`}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}


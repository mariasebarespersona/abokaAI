'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Save, RefreshCw, TrendingUp, TrendingDown, DollarSign, 
  Home, Hammer, Landmark, Receipt, Store, Flag,
  ChevronDown, ChevronRight, Calculator, Percent,
  Building, FileText, Download
} from 'lucide-react';
import * as XLSX from 'xlsx';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface EstudioItem {
  id: string;
  key: string;           // Unique identifier like "compra_precio"
  label: string;         // Display name
  category: string;      // COMPRA, REFORMA, FINANCIERO, GESTIONES, VENTA
  subcategory?: string;  // Optional grouping within category
  estimado: number | null;
  real: number | null;
  isFormula?: boolean;   // If true, this row is calculated
  formula?: string;      // Description of formula for display
  order: number;         // Sort order
}

interface AbokaExcelProps {
  propertyId: string | null;
  onCellUpdate?: (key: string, value: number) => void;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TEMPLATE DEFINITION - Estudio Económico Inmobiliario
// ═══════════════════════════════════════════════════════════════════════════════

const TEMPLATE_ITEMS: Omit<EstudioItem, 'id' | 'estimado' | 'real'>[] = [
  // ─────────────────────────────────────────────────────────────────────────────
  // COMPRA DEL ACTIVO
  // ─────────────────────────────────────────────────────────────────────────────
  { key: 'compra_precio', label: 'Precio Compra Activo', category: 'COMPRA', order: 1 },
  { key: 'compra_itp', label: 'ITP (Impuesto Transmisiones)', category: 'COMPRA', order: 2 },
  { key: 'compra_notaria', label: 'Notaría + Registro + Gestoría', category: 'COMPRA', order: 3 },
  { key: 'compra_ibi', label: 'IBI Prorrateado', category: 'COMPRA', order: 4 },
  { key: 'compra_gestion', label: 'Gestión ABOKA 1%', category: 'COMPRA', order: 5 },
  { key: 'compra_total', label: 'TOTAL COMPRA', category: 'COMPRA', order: 6, isFormula: true, formula: 'Suma automática' },

  // ─────────────────────────────────────────────────────────────────────────────
  // REFORMA
  // ─────────────────────────────────────────────────────────────────────────────
  { key: 'reforma_proyecto', label: 'Proyecto / Arquitecto', category: 'REFORMA', subcategory: 'Licencias', order: 10 },
  { key: 'reforma_licencia', label: 'Licencia de Obra / ICIO', category: 'REFORMA', subcategory: 'Licencias', order: 11 },
  { key: 'reforma_contrata', label: 'Contrata de Obra', category: 'REFORMA', subcategory: 'Obra', order: 12 },
  { key: 'reforma_cocina', label: 'Mobiliario Cocina + Electros', category: 'REFORMA', subcategory: 'Materiales', order: 13 },
  { key: 'reforma_banos', label: 'Sanitarios Baños + Griferías', category: 'REFORMA', subcategory: 'Materiales', order: 14 },
  { key: 'reforma_suelos', label: 'Tarima / Suelos', category: 'REFORMA', subcategory: 'Materiales', order: 15 },
  { key: 'reforma_carpinteria', label: 'Armarios y Carpintería', category: 'REFORMA', subcategory: 'Materiales', order: 16 },
  { key: 'reforma_ac', label: 'Aire Acondicionado', category: 'REFORMA', subcategory: 'Materiales', order: 17 },
  { key: 'reforma_otros', label: 'Otros Materiales', category: 'REFORMA', subcategory: 'Materiales', order: 18 },
  { key: 'reforma_amueblamiento', label: 'Amueblamiento / Home Staging', category: 'REFORMA', subcategory: 'Decoración', order: 19 },
  { key: 'reforma_contingencia', label: 'Contingencia (5-10%)', category: 'REFORMA', order: 20 },
  { key: 'reforma_total', label: 'TOTAL REFORMA', category: 'REFORMA', order: 21, isFormula: true, formula: 'Suma automática' },

  // ─────────────────────────────────────────────────────────────────────────────
  // FINANCIEROS
  // ─────────────────────────────────────────────────────────────────────────────
  { key: 'fin_constitucion', label: 'Gastos Constitución Hipoteca', category: 'FINANCIERO', order: 30 },
  { key: 'fin_tasacion', label: 'Tasación Oficial', category: 'FINANCIERO', order: 31 },
  { key: 'fin_intereses', label: 'Intereses Soportados', category: 'FINANCIERO', order: 32 },
  { key: 'fin_cancelacion', label: 'Gastos Cancelación Hipoteca', category: 'FINANCIERO', order: 33 },
  { key: 'fin_seguro', label: 'Seguro Multirriesgo', category: 'FINANCIERO', order: 34 },
  { key: 'fin_total', label: 'TOTAL FINANCIEROS', category: 'FINANCIERO', order: 35, isFormula: true, formula: 'Suma automática' },

  // ─────────────────────────────────────────────────────────────────────────────
  // GESTIONES
  // ─────────────────────────────────────────────────────────────────────────────
  { key: 'gest_comunidad', label: 'Comunidad de Propietarios', category: 'GESTIONES', order: 40 },
  { key: 'gest_ibi', label: 'IBI Anual', category: 'GESTIONES', order: 41 },
  { key: 'gest_suministros', label: 'Suministros (Luz, Gas, Agua)', category: 'GESTIONES', order: 42 },
  { key: 'gest_plusvalia', label: 'Plusvalía Municipal', category: 'GESTIONES', order: 43 },
  { key: 'gest_comision', label: 'Comisión Agencia Venta', category: 'GESTIONES', order: 44 },
  { key: 'gest_total', label: 'TOTAL GESTIONES', category: 'GESTIONES', order: 45, isFormula: true, formula: 'Suma automática' },

  // ─────────────────────────────────────────────────────────────────────────────
  // VENTA / INGRESOS
  // ─────────────────────────────────────────────────────────────────────────────
  { key: 'venta_precio', label: 'Precio Venta Vivienda', category: 'VENTA', order: 50 },
  { key: 'venta_alquileres', label: 'Alquileres Temporales', category: 'VENTA', order: 51 },
  { key: 'venta_total', label: 'TOTAL INGRESOS', category: 'VENTA', order: 52, isFormula: true, formula: 'Suma automática' },
];

// Category configuration
const CATEGORY_CONFIG: Record<string, { 
  icon: React.ElementType; 
  color: string; 
  bgColor: string;
  borderColor: string;
  label: string;
  isExpense: boolean;
}> = {
  'COMPRA': { 
    icon: Home, 
    color: 'text-emerald-600', 
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    label: 'Compra del Activo',
    isExpense: true
  },
  'REFORMA': { 
    icon: Hammer, 
    color: 'text-amber-600', 
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    label: 'Reforma y Obra',
    isExpense: true
  },
  'FINANCIERO': { 
    icon: Landmark, 
    color: 'text-blue-600', 
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    label: 'Gastos Financieros',
    isExpense: true
  },
  'GESTIONES': { 
    icon: Receipt, 
    color: 'text-purple-600', 
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    label: 'Gestiones y Otros',
    isExpense: true
  },
  'VENTA': { 
    icon: Store, 
    color: 'text-rose-600', 
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-200',
    label: 'Venta e Ingresos',
    isExpense: false
  },
};

const CATEGORY_ORDER = ['COMPRA', 'REFORMA', 'FINANCIERO', 'GESTIONES', 'VENTA'];

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export function AbokaExcel({ propertyId, onCellUpdate }: AbokaExcelProps) {
  const [items, setItems] = useState<EstudioItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(CATEGORY_ORDER)
  );

  const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080';

  // ─────────────────────────────────────────────────────────────────────────────
  // Initialize template for property
  // ─────────────────────────────────────────────────────────────────────────────
  const initializeTemplate = useCallback(() => {
    const templateItems: EstudioItem[] = TEMPLATE_ITEMS.map((item, idx) => ({
      ...item,
      id: `${propertyId}-${item.key}`,
      estimado: null,
      real: null,
    }));
    setItems(templateItems);
  }, [propertyId]);

  // ─────────────────────────────────────────────────────────────────────────────
  // Load data from backend
  // ─────────────────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!propertyId) {
      setItems([]);
      return;
    }
    
    setLoading(true);
    
    // Initialize template immediately so user sees something
    initializeTemplate();
    
    // Try to load existing data from backend (async, non-blocking)
    fetch(`${BACKEND_URL}/api/estudio/${propertyId}`)
      .then(res => res.json())
      .then(data => {
        if (data.ok && data.items && data.items.length > 0) {
          // Merge backend data with template
          const templateItems = TEMPLATE_ITEMS.map(template => {
            const backendItem = data.items.find((i: any) => i.key === template.key);
            return {
              ...template,
              id: backendItem?.id || `${propertyId}-${template.key}`,
              estimado: backendItem?.estimado ?? null,
              real: backendItem?.real ?? null,
            };
          });
          setItems(templateItems);
        }
        // If no backend data, keep the local template already initialized
      })
      .catch(err => {
        console.warn('Backend unavailable, using local template:', err.message);
        // Template already initialized, nothing to do
      })
      .finally(() => setLoading(false));
  }, [propertyId, BACKEND_URL, initializeTemplate]);

  // ─────────────────────────────────────────────────────────────────────────────
  // Calculate totals (formulas)
  // ─────────────────────────────────────────────────────────────────────────────
  const calculatedItems = useMemo(() => {
    return items.map(item => {
      if (!item.isFormula) return item;

      // Calculate category total
      const category = item.category;
      const categoryItems = items.filter(i => 
        i.category === category && !i.isFormula
      );
      
      const totalEstimado = categoryItems.reduce((sum, i) => sum + (i.estimado || 0), 0);
      const totalReal = categoryItems.reduce((sum, i) => sum + (i.real || 0), 0);

      return {
        ...item,
        estimado: totalEstimado,
        real: totalReal,
      };
    });
  }, [items]);

  // ─────────────────────────────────────────────────────────────────────────────
  // Calculate summary metrics
  // ─────────────────────────────────────────────────────────────────────────────
  const summary = useMemo(() => {
    const totals = calculatedItems.filter(i => i.isFormula);
    
    const totalGastos = totals
      .filter(t => CATEGORY_CONFIG[t.category]?.isExpense)
      .reduce((sum, t) => sum + (t.estimado || 0), 0);
    
    const totalIngresos = totals
      .filter(t => !CATEGORY_CONFIG[t.category]?.isExpense)
      .reduce((sum, t) => sum + (t.estimado || 0), 0);

    const beneficioBruto = totalIngresos - totalGastos;
    const honorariosAboka = beneficioBruto > 0 ? beneficioBruto * 0.20 : 0; // 20% success fee
    const beneficioNeto = beneficioBruto - honorariosAboka;
    const roi = totalGastos > 0 ? (beneficioNeto / totalGastos) * 100 : 0;

    // Real values
    const totalGastosReal = totals
      .filter(t => CATEGORY_CONFIG[t.category]?.isExpense)
      .reduce((sum, t) => sum + (t.real || 0), 0);
    
    const totalIngresosReal = totals
      .filter(t => !CATEGORY_CONFIG[t.category]?.isExpense)
      .reduce((sum, t) => sum + (t.real || 0), 0);

    const beneficioBrutoReal = totalIngresosReal - totalGastosReal;
    const honorariosAbokaReal = beneficioBrutoReal > 0 ? beneficioBrutoReal * 0.20 : 0;
    const beneficioNetoReal = beneficioBrutoReal - honorariosAbokaReal;
    const roiReal = totalGastosReal > 0 ? (beneficioNetoReal / totalGastosReal) * 100 : 0;

    return {
      totalGastos,
      totalIngresos,
      beneficioBruto,
      honorariosAboka,
      beneficioNeto,
      roi,
      totalGastosReal,
      totalIngresosReal,
      beneficioBrutoReal,
      honorariosAbokaReal,
      beneficioNetoReal,
      roiReal,
    };
  }, [calculatedItems]);

  // ─────────────────────────────────────────────────────────────────────────────
  // Handle cell changes
  // ─────────────────────────────────────────────────────────────────────────────
  const handleValueChange = (key: string, field: 'estimado' | 'real', value: string) => {
    const numValue = value === '' ? null : parseFloat(value.replace(/[^\d.-]/g, ''));
    
    setItems(prev => prev.map(item => 
      item.key === key 
        ? { ...item, [field]: isNaN(numValue as number) ? null : numValue }
        : item
    ));
  };

  const saveCell = useCallback(async (key: string, field: 'estimado' | 'real', value: number | null) => {
    if (!propertyId) return;
    
    setSavingKey(key);
    try {
      await fetch(`${BACKEND_URL}/api/estudio/${propertyId}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, field, value })
      });
      
      onCellUpdate?.(key, value || 0);
    } catch (e) {
      console.error('Save failed:', e);
    } finally {
      setTimeout(() => setSavingKey(null), 300);
    }
  }, [propertyId, BACKEND_URL, onCellUpdate]);

  // ─────────────────────────────────────────────────────────────────────────────
  // Toggle category expansion
  // ─────────────────────────────────────────────────────────────────────────────
  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  // ─────────────────────────────────────────────────────────────────────────────
  // Export to Excel
  // ─────────────────────────────────────────────────────────────────────────────
  const downloadExcel = useCallback(() => {
    // Prepare data for Excel
    const excelData: any[][] = [];
    
    // Header row
    excelData.push(['ESTUDIO ECONÓMICO - ABOKA AI']);
    excelData.push([]);
    excelData.push(['Concepto', 'Estimación (€)', 'Real (€)']);
    
    // Add items by category
    CATEGORY_ORDER.forEach(category => {
      const categoryItems = calculatedItems.filter(item => item.category === category);
      const config = CATEGORY_CONFIG[category];
      
      // Category header
      excelData.push([]);
      excelData.push([`${category} - ${config.label}`, '', '']);
      
      // Items
      categoryItems.forEach(item => {
        if (item.isFormula) {
          excelData.push([
            `  >> ${item.label}`,
            item.estimado || 0,
            item.real || 0
          ]);
        } else {
          excelData.push([
            `  ${item.label}`,
            item.estimado || 0,
            item.real || 0
          ]);
        }
      });
    });
    
    // Summary section
    excelData.push([]);
    excelData.push(['RESUMEN', '', '']);
    excelData.push(['Total Gastos', summary.totalGastos, summary.totalGastosReal]);
    excelData.push(['Total Ingresos', summary.totalIngresos, summary.totalIngresosReal]);
    excelData.push(['Beneficio Bruto', summary.beneficioBruto, summary.beneficioBrutoReal]);
    excelData.push(['Honorarios ABOKA (20%)', summary.honorariosAboka, summary.honorariosAbokaReal]);
    excelData.push(['Beneficio Neto', summary.beneficioNeto, summary.beneficioNetoReal]);
    excelData.push(['ROI %', `${summary.roi.toFixed(2)}%`, `${summary.roiReal.toFixed(2)}%`]);
    
    // Create workbook and worksheet
    const wb = XLSX.utils.book_new();
    const worksheet = XLSX.utils.aoa_to_sheet(excelData);
    
    // Set column widths
    worksheet['!cols'] = [
      { wch: 40 }, // Concepto
      { wch: 18 }, // Estimación
      { wch: 18 }, // Real
    ];
    
    // Add worksheet to workbook
    XLSX.utils.book_append_sheet(wb, worksheet, 'Estudio Económico');
    
    // Generate filename with date
    const date = new Date().toISOString().split('T')[0];
    const filename = `estudio_economico_${date}.xlsx`;
    
    // Download
    XLSX.writeFile(wb, filename);
  }, [calculatedItems, summary]);

  // ─────────────────────────────────────────────────────────────────────────────
  // Format helpers
  // ─────────────────────────────────────────────────────────────────────────────
  const formatCurrency = (val: number | null) => {
    if (val === null || val === 0) return '-';
    return new Intl.NumberFormat('es-ES', { 
      style: 'currency', 
      currency: 'EUR', 
      maximumFractionDigits: 0 
    }).format(val);
  };

  const formatPercent = (val: number) => {
    return `${val.toFixed(2)}%`;
  };

  // ─────────────────────────────────────────────────────────────────────────────
  // Group items by category
  // ─────────────────────────────────────────────────────────────────────────────
  const groupedItems = useMemo(() => {
    const grouped: Record<string, EstudioItem[]> = {};
    for (const item of calculatedItems) {
      if (!grouped[item.category]) {
        grouped[item.category] = [];
      }
      grouped[item.category].push(item);
    }
    // Sort items within each category
    for (const cat of Object.keys(grouped)) {
      grouped[cat].sort((a, b) => a.order - b.order);
    }
    return grouped;
  }, [calculatedItems]);

  // ─────────────────────────────────────────────────────────────────────────────
  // No property selected
  // ─────────────────────────────────────────────────────────────────────────────
  if (!propertyId) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-400 p-8 bg-white rounded-xl border border-slate-200">
        <FileText size={48} className="mb-4 opacity-30" />
        <h3 className="text-lg font-medium text-slate-500">Estudio Económico</h3>
        <p className="text-sm text-center mt-2">
          Selecciona una propiedad para ver su estudio económico
        </p>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Loading state
  // ─────────────────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-white rounded-xl border border-slate-200">
        <RefreshCw size={32} className="animate-spin text-blue-500 mb-4" />
        <p className="text-sm text-slate-500">Cargando estudio económico...</p>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <div className="h-full flex flex-col bg-white rounded-xl border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/25">
              <Calculator size={20} className="text-white" />
            </div>
        <div>
              <h2 className="font-bold text-slate-800">Estudio Económico</h2>
              <p className="text-xs text-slate-500">Análisis de inversión inmobiliaria</p>
            </div>
        </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={downloadExcel}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-600 hover:text-emerald-700 transition-colors text-sm font-medium"
              title="Descargar Excel"
            >
              <Download size={14} />
              <span>Excel</span>
            </button>
            <button 
              onClick={() => initializeTemplate()}
              className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
              title="Reiniciar plantilla"
            >
            <RefreshCw size={16} />
          </button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex-shrink-0">
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-white rounded-lg p-3 border border-slate-200 shadow-sm">
            <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Total Gastos</p>
            <p className="text-lg font-bold text-red-600 font-mono">{formatCurrency(summary.totalGastos)}</p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-slate-200 shadow-sm">
            <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Ingresos</p>
            <p className="text-lg font-bold text-emerald-600 font-mono">{formatCurrency(summary.totalIngresos)}</p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-slate-200 shadow-sm">
            <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Beneficio Neto</p>
            <p className={`text-lg font-bold font-mono ${summary.beneficioNeto >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {formatCurrency(summary.beneficioNeto)}
            </p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-slate-200 shadow-sm">
            <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">ROI</p>
            <p className={`text-lg font-bold font-mono ${summary.roi >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {formatPercent(summary.roi)}
            </p>
          </div>
        </div>
      </div>

      {/* Table Header */}
      <div className="grid grid-cols-12 gap-2 px-4 py-2 bg-slate-900 text-slate-300 text-xs font-semibold uppercase tracking-wider flex-shrink-0">
        <div className="col-span-6">Concepto</div>
        <div className="col-span-3 text-right">Estimación (€)</div>
        <div className="col-span-3 text-right">Real (€)</div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto">
        {CATEGORY_ORDER.map(category => {
          const config = CATEGORY_CONFIG[category];
          const categoryItems = groupedItems[category] || [];
          const isExpanded = expandedCategories.has(category);
          const Icon = config.icon;

          // Get category total
          const totalItem = categoryItems.find(i => i.isFormula);
                  
                  return (
            <div key={category} className="border-b border-slate-100 last:border-b-0">
                    {/* Category Header */}
              <button
                onClick={() => toggleCategory(category)}
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
                  <span className={`font-bold text-sm ${config.color}`}>{category}</span>
                  <span className="text-xs text-slate-500 ml-2">{config.label}</span>
                </div>
                <div className="text-right">
                  <span className={`font-bold font-mono ${config.color}`}>
                    {formatCurrency(totalItem?.estimado || 0)}
                  </span>
                </div>
              </button>

              {/* Category Items */}
              {isExpanded && (
                <div className="bg-white">
                  {categoryItems.filter(item => !item.isFormula).map(item => (
                    <div 
                      key={item.key}
                      className="grid grid-cols-12 gap-2 px-4 py-2 border-b border-slate-50 hover:bg-slate-50 transition-colors items-center"
                    >
                      {/* Label */}
                      <div className="col-span-6 text-sm text-slate-700 pl-8">
                        {item.subcategory && (
                          <span className="text-[10px] text-slate-400 uppercase mr-2">
                            {item.subcategory}:
                          </span>
                        )}
                        {item.label}
                      </div>
                      
                      {/* Estimado Input */}
                      <div className="col-span-3">
                        <div className="relative">
                            <input
                            type="text"
                            inputMode="numeric"
                            className="w-full text-right bg-transparent focus:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 px-2 py-1 rounded text-slate-700 font-mono text-sm"
                            value={item.estimado ?? ''}
                            onChange={(e) => handleValueChange(item.key, 'estimado', e.target.value)}
                            onBlur={() => saveCell(item.key, 'estimado', item.estimado)}
                              placeholder="0"
                            />
                          {savingKey === item.key && (
                            <Save className="w-3 h-3 text-blue-400 absolute right-1 top-1/2 -translate-y-1/2 animate-pulse" />
                            )}
                          </div>
                      </div>
                      
                      {/* Real Input */}
                      <div className="col-span-3">
                        <input
                          type="text"
                          inputMode="numeric"
                          className="w-full text-right bg-slate-50 focus:bg-emerald-50 focus:outline-none focus:ring-2 focus:ring-emerald-500 px-2 py-1 rounded text-slate-700 font-mono text-sm"
                          value={item.real ?? ''}
                          onChange={(e) => handleValueChange(item.key, 'real', e.target.value)}
                          onBlur={() => saveCell(item.key, 'real', item.real)}
                          placeholder="0"
                        />
                      </div>
                    </div>
                  ))}
                  
                  {/* Category Total Row */}
                  {totalItem && (
                    <div className={`grid grid-cols-12 gap-2 px-4 py-2 ${config.bgColor} border-t ${config.borderColor}`}>
                      <div className={`col-span-6 text-sm font-bold ${config.color} pl-8`}>
                        {totalItem.label}
                      </div>
                      <div className={`col-span-3 text-right font-bold font-mono ${config.color}`}>
                        {formatCurrency(totalItem.estimado)}
                      </div>
                      <div className={`col-span-3 text-right font-bold font-mono ${config.color}`}>
                        {formatCurrency(totalItem.real)}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
                  );
                })}
      </div>

      {/* Footer Summary */}
      <div className="bg-slate-900 text-white px-4 py-4 flex-shrink-0">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Estimación</p>
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Beneficio Bruto:</span>
                <span className={`font-mono ${summary.beneficioBruto >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {formatCurrency(summary.beneficioBruto)}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Honorarios ABOKA (20%):</span>
                <span className="font-mono text-amber-400">{formatCurrency(summary.honorariosAboka)}</span>
              </div>
              <div className="flex justify-between text-sm font-bold border-t border-slate-700 pt-1 mt-1">
                <span className="text-white">Beneficio Neto:</span>
                <span className={`font-mono ${summary.beneficioNeto >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {formatCurrency(summary.beneficioNeto)} ({formatPercent(summary.roi)})
                </span>
              </div>
            </div>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Real</p>
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Beneficio Bruto:</span>
                <span className={`font-mono ${summary.beneficioBrutoReal >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {formatCurrency(summary.beneficioBrutoReal)}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Honorarios ABOKA (20%):</span>
                <span className="font-mono text-amber-400">{formatCurrency(summary.honorariosAbokaReal)}</span>
      </div>
              <div className="flex justify-between text-sm font-bold border-t border-slate-700 pt-1 mt-1">
                <span className="text-white">Beneficio Neto:</span>
                <span className={`font-mono ${summary.beneficioNetoReal >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {formatCurrency(summary.beneficioNetoReal)} ({formatPercent(summary.roiReal)})
          </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

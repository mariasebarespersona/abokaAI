'use client'

import React, { useState, useEffect, useRef } from 'react'
import { PropertiesDrawer } from '@/components/PropertiesDrawer'
import { HomeProperty } from '@/types/maninos'
import { Menu, Building2, FileSpreadsheet, FolderOpen, LayoutDashboard } from 'lucide-react'
import { AbokaExcel } from '@/components/aboka/AbokaExcel'
import { ArmarioDigital } from '@/components/aboka/ArmarioDigital'
import { PropertyDashboard } from '@/components/aboka/PropertyDashboard'
import { ChatPanel } from '@/components/ChatPanel'

// We need to fetch properties to pass to the Drawer
// This logic is duplicated from ChatPage but necessary for the layout level if we lift state
// ideally we would refactor ChatPage to be just the "Right Column" component

export default function AbokaWorkspace() {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [propertiesList, setPropertiesList] = useState<HomeProperty[]>([])
  
  // Global Selection State
  const [selectedPropertyId, setSelectedPropertyId] = useState<string | null>(null)
  
  // Property Creation Mode - only active when "New Evaluation" is clicked
  const [isCreatingProperty, setIsCreatingProperty] = useState(false)
  
  // Active Panel Tab: 'dashboard', 'excel' or 'docs'
  const [activePanel, setActivePanel] = useState<'dashboard' | 'excel' | 'docs'>('dashboard')
  
  // Refresh key - changes when chat updates financial data
  const [excelRefreshKey, setExcelRefreshKey] = useState(0)
  
  // Called by ChatPanel when financial data is updated via chat
  const handleFinancialDataUpdated = () => {
    setExcelRefreshKey(prev => prev + 1)
  }
  
  // Load initial state
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedId = localStorage.getItem('aboka_property_id')
      if (storedId) setSelectedPropertyId(storedId)
    }
    fetchPropertiesList()
  }, [])

  const fetchPropertiesList = async () => {
    try {
      const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080'
      const res = await fetch(`${BACKEND_URL}/api/properties`)
      const json = await res.json()
      if (json.ok) setPropertiesList(json.properties)
    } catch (e) {
      console.error('Failed to fetch properties', e)
    }
  }

  const handleSelectProperty = (id: string) => {
    setSelectedPropertyId(id)
    if (typeof window !== 'undefined') {
      localStorage.setItem('aboka_property_id', id)
    }
    // Force a reload of the chat component or trigger an event? 
    // For now, simple state update propagates down
  }

  const handleNewEvaluation = () => {
    setSelectedPropertyId(null)
    localStorage.removeItem('aboka_property_id')
    setIsCreatingProperty(true) // Activate creation mode
  }

  const handlePropertyCreated = (newPropertyId: string, propertyName: string) => {
    setSelectedPropertyId(newPropertyId)
    localStorage.setItem('aboka_property_id', newPropertyId)
    setIsCreatingProperty(false) // Deactivate creation mode
    fetchPropertiesList() // Refresh properties list
  }

  // Get selected property name for display
  const selectedProperty = propertiesList.find(p => p.id === selectedPropertyId)
  const selectedPropertyName = selectedProperty?.name || null

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden font-sans text-slate-900">
      
      {/* DRAWER (Modal/Overlay style for now, but triggered from sidebar) */}
      <PropertiesDrawer
          isOpen={isDrawerOpen}
          onClose={() => setIsDrawerOpen(false)}
          properties={propertiesList}
          onSelectProperty={handleSelectProperty}
          currentPropertyId={selectedPropertyId}
          onNewProperty={handleNewEvaluation}
          onPropertyDeleted={fetchPropertiesList}
      />

      {/* COLUMN 1: NAVIGATION / SIDEBAR (Mini) */}
      <aside className="w-16 bg-slate-900 flex flex-col items-center py-6 gap-6 z-30 flex-shrink-0 border-r border-slate-800">
        <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white font-bold shadow-lg shadow-blue-900/50">
          A
        </div>
        <nav className="flex flex-col gap-4 w-full items-center">
            <button
                onClick={() => {
                    fetchPropertiesList()
                    setIsDrawerOpen(true)
                }}
                className="p-3 rounded-xl bg-slate-800 text-white hover:bg-slate-700 transition-colors tooltip"
                title="Propiedades"
            >
                <Menu size={20} />
            </button>
        </nav>
      </aside>

      {/* MAIN WORKSPACE SPLIT */}
      <div className="flex flex-1 min-w-0">
        
        {/* COLUMN 2: MAIN CONTENT AREA - Excel / Armario (Center Stage - 55%) */}
        <section className="flex-1 flex flex-col min-w-[500px] border-r border-slate-200 bg-slate-50/50">
          
          {/* Tab Navigation */}
          <div className="flex items-center gap-1 px-4 pt-4 pb-2 bg-white border-b border-slate-100">
            <button
              onClick={() => setActivePanel('dashboard')}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activePanel === 'dashboard'
                  ? 'bg-slate-800 text-white shadow-lg shadow-slate-500/25'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <LayoutDashboard size={16} />
              Dashboard
            </button>
            <button
              onClick={() => setActivePanel('excel')}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activePanel === 'excel'
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <FileSpreadsheet size={16} />
              Estudio Económico
            </button>
            <button
              onClick={() => setActivePanel('docs')}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activePanel === 'docs'
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <FolderOpen size={16} />
              Armario Digital
            </button>
            
            {/* Property Name Badge */}
            {selectedPropertyName && (
              <div className="ml-auto flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-lg">
                <Building2 size={14} className="text-slate-500" />
                <span className="text-sm font-medium text-slate-700 max-w-[200px] truncate">
                  {selectedPropertyName}
                </span>
              </div>
            )}
          </div>
          
          {/* Panel Content */}
          <div className="flex-1 p-4 overflow-hidden">
            {selectedPropertyId ? (
              activePanel === 'dashboard' ? (
                <PropertyDashboard 
                  propertyId={selectedPropertyId}
                  propertyName={selectedPropertyName}
                />
              ) : activePanel === 'excel' ? (
                <AbokaExcel propertyId={selectedPropertyId} key={`excel-${excelRefreshKey}`} />
              ) : (
                <ArmarioDigital 
                  key={`armario-${selectedPropertyId}`}
                  propertyId={selectedPropertyId} 
                  propertyName={selectedPropertyName}
                />
              )
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50">
                <Building2 size={48} className="mb-4 opacity-20" />
                <h3 className="text-lg font-medium text-slate-600">Ninguna propiedad seleccionada</h3>
                <p className="text-sm">Selecciona una propiedad del menú izquierdo para ver su balance.</p>
                <button 
                  onClick={() => setIsDrawerOpen(true)}
                  className="mt-4 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Abrir Lista
                </button>
              </div>
            )}
          </div>
        </section>

        {/* COLUMN 3: CHAT (Right Sidebar - 35%) */}
        <section className="w-[450px] flex-shrink-0 bg-white shadow-xl z-10 flex flex-col h-full">
           <ChatPanel 
             propertyId={selectedPropertyId}
             propertyName={selectedPropertyName}
             isCreatingProperty={isCreatingProperty}
             onCancelCreation={() => setIsCreatingProperty(false)}
             onPropertyCreated={handlePropertyCreated}
             onFinancialDataUpdated={handleFinancialDataUpdated}
           />
        </section>

      </div>
    </div>
  )
}

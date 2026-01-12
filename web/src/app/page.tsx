'use client'

import React, { useState, useEffect, useRef } from 'react'
import { PropertiesDrawer } from '@/components/PropertiesDrawer'
import { MobileHomeProperty } from '@/types/maninos'
import { Bot, Menu, Building2 } from 'lucide-react'
import { ChatPanel } from '@/components/ChatPanel'
import { AbokaExcel } from '@/components/aboka/AbokaExcel'

// We need to fetch properties to pass to the Drawer

export default function AbokaWorkspace() {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [propertiesList, setPropertiesList] = useState<MobileHomeProperty[]>([])
  
  // Global Selection State
  const [selectedPropertyId, setSelectedPropertyId] = useState<string | null>(null)
  
  // Load initial state
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedId = localStorage.getItem('maninos_property_id')
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
      localStorage.setItem('maninos_property_id', id)
    }
    // Force a reload of the chat component or trigger an event? 
    // For now, simple state update propagates down
  }

  const handleNewEvaluation = () => {
    setSelectedPropertyId(null)
    localStorage.removeItem('maninos_property_id')
  }

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
        
        {/* COLUMN 2: ABOKA EXCEL (Center Stage - 55%) */}
        <section className="flex-1 p-4 flex flex-col min-w-[500px] border-r border-slate-200 bg-slate-50/50">
          {selectedPropertyId ? (
            <AbokaExcel propertyId={selectedPropertyId} />
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
        </section>

        {/* COLUMN 3: CHAT (Right Sidebar - 35%) */}
        <section className="w-[450px] flex-shrink-0 bg-white shadow-xl z-10 flex flex-col h-full">
           <div className="h-full overflow-hidden">
             <ChatPanel propertyId={selectedPropertyId} />
           </div>
        </section>

      </div>
    </div>
  )
}

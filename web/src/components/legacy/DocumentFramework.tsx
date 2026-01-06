import React from 'react'

interface Document {
  document_group: string
  document_subgroup: string
  document_name: string
  storage_key?: string
  document_kind?: string
  placeholder?: boolean
  due_date?: string
  metadata?: any
}

interface DocumentFrameworkProps {
  uploaded: Document[]
  pending: Document[]
}

const StatusBadge = ({ uploaded, total }: { uploaded: number, total: number }) => {
  const pct = total > 0 ? Math.round((uploaded / total) * 100) : 0
  const color = pct === 100 ? 'bg-emerald-100 text-emerald-800' : pct > 0 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-500'
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>
      {uploaded}/{total} ({pct}%)
    </span>
  )
}

const DocItem = ({ doc, isUploaded }: { doc: Document, isUploaded: boolean }) => (
  <div className={`group flex items-center gap-2 p-2 rounded-lg border border-transparent hover:border-[color:var(--border-subtle)] hover:bg-white transition-all ${isUploaded ? 'opacity-100' : 'opacity-70'}`}>
    <div className={`w-5 h-5 flex items-center justify-center rounded-full text-[10px] ${isUploaded ? 'bg-[color:var(--brand-100)] text-[color:var(--brand-900)]' : 'bg-slate-100 text-slate-400'}`}>
      {isUploaded ? '✓' : '•'}
    </div>
    <div className="flex-1 min-w-0">
      <div className={`text-xs truncate ${isUploaded ? 'text-[color:var(--text-primary)] font-medium' : 'text-[color:var(--text-secondary)]'}`}>
        {doc.document_name}
      </div>
      {doc.document_subgroup && (
        <div className="text-[10px] text-[color:var(--text-tertiary)] truncate">
          {doc.document_subgroup}
        </div>
      )}
    </div>
    {doc.document_kind === 'factura' && (
        <span className="text-[10px] bg-amber-50 text-amber-600 px-1.5 py-0.5 rounded border border-amber-100">Factura</span>
    )}
  </div>
)

const SectionCard = ({ title, docs }: { title: string, docs: Document[] }) => {
    const uploadedCount = docs.filter(d => d.storage_key).length
    
    return (
        <div className="rounded-xl border border-[color:var(--border-subtle)] bg-white shadow-sm overflow-hidden">
            <div className="flex items-center justify-between p-3 border-b border-[color:var(--border-subtle)] bg-[color:var(--slate-50)]">
                <div className="flex items-center gap-2 font-bold text-sm text-[color:var(--text-primary)]">
                    <span className="text-lg">📂</span>
                    {title || 'General'}
                </div>
                <StatusBadge uploaded={uploadedCount} total={docs.length} />
            </div>
            <div className="p-2 space-y-1 max-h-[300px] overflow-y-auto scrollbar-thin">
                {docs.length > 0 ? (
                    docs.map((doc, i) => <DocItem key={i} doc={doc} isUploaded={!!doc.storage_key} />)
                ) : (
                    <div className="p-4 text-center text-xs text-[color:var(--text-tertiary)] italic">Sin documentos</div>
                )}
            </div>
        </div>
    )
}

export const DocumentFramework = ({ uploaded, pending }: DocumentFrameworkProps) => {
  const allDocs = [...uploaded, ...pending]

  // Dynamic Grouping
  const groups: Record<string, Document[]> = {}
  
  allDocs.forEach(doc => {
    const groupName = doc.document_group || 'General'
    if (!groups[groupName]) {
      groups[groupName] = []
    }
    groups[groupName].push(doc)
  })

  // Sort groups: "Compra" or "Acquisition" first, then others alphabetically
  const sortedGroupNames = Object.keys(groups).sort((a, b) => {
    const priority = ['COMPRA', 'ADQUISICIÓN', 'ACQUISITION', 'INSPECTION', 'CONTRACT']
    const idxA = priority.indexOf(a.toUpperCase())
    const idxB = priority.indexOf(b.toUpperCase())
    
    if (idxA !== -1 && idxB !== -1) return idxA - idxB
    if (idxA !== -1) return -1
    if (idxB !== -1) return 1
    return a.localeCompare(b)
  })

  if (allDocs.length === 0) {
    return (
      <div className="text-center p-8 text-[color:var(--text-tertiary)] text-sm">
        No hay documentos asociados a esta propiedad.
      </div>
    )
  }

  return (
    <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-4">
      {sortedGroupNames.map(groupName => (
        <SectionCard 
          key={groupName}
          title={groupName}
          docs={groups[groupName]}
        />
      ))}
    </div>
  )
}

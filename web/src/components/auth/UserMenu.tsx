'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from './AuthProvider'
import { User, LogOut, Settings } from 'lucide-react'

export function UserMenu() {
  const { user, signOut, loading } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const router = useRouter()

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSignOut = async () => {
    await signOut()
    router.push('/login')
    router.refresh()
  }

  if (loading) {
    return (
      <div className="w-8 h-8 rounded-full bg-slate-700 animate-pulse" />
    )
  }

  if (!user) {
    return (
      <button
        onClick={() => router.push('/login')}
        className="px-4 py-2 text-sm font-medium text-white bg-amber-500 hover:bg-amber-600 rounded-lg transition-colors"
      >
        Iniciar sesión
      </button>
    )
  }

  const initials = user.user_metadata?.full_name
    ? user.user_metadata.full_name.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2)
    : user.email?.slice(0, 2).toUpperCase() || '??'

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 p-1 rounded-lg hover:bg-slate-700/50 transition-colors"
      >
        <div className="w-8 h-8 rounded-full bg-amber-500/20 border border-amber-500/50 flex items-center justify-center text-amber-500 text-sm font-medium">
          {initials}
        </div>
        <span className="text-sm text-slate-300 hidden sm:block max-w-[150px] truncate">
          {user.user_metadata?.full_name || user.email}
        </span>
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-slate-800 border border-slate-700 rounded-lg shadow-xl py-1 z-50">
          <div className="px-4 py-3 border-b border-slate-700">
            <p className="text-sm font-medium text-white truncate">
              {user.user_metadata?.full_name || 'Usuario'}
            </p>
            <p className="text-xs text-slate-400 truncate">{user.email}</p>
          </div>

          <button
            onClick={() => {
              setIsOpen(false)
              // router.push('/settings')  // If you have a settings page
            }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-700/50 transition-colors"
          >
            <Settings className="w-4 h-4" />
            Configuración
          </button>

          <hr className="border-slate-700 my-1" />

          <button
            onClick={handleSignOut}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Cerrar sesión
          </button>
        </div>
      )}
    </div>
  )
}


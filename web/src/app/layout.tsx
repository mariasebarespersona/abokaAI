import './globals.css'
import React from 'react'
import type { Metadata } from 'next'
import Image from 'next/image'
import { Inter, Lora } from 'next/font/google'

const inter = Inter({ 
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const lora = Lora({
  subsets: ['latin'],
  variable: '--font-lora',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'ABOKA AI',
  description: 'Plataforma inteligente para gestión de reformas y flipping inmobiliario.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${inter.variable} ${lora.variable}`}>
      <body className="h-screen overflow-hidden font-sans">
        {children}
      </body>
    </html>
  )
}

'use client'

import { Toaster as SonnerToaster, toast } from 'sonner'

interface ToasterProps {
  position?:
    | 'top-left'
    | 'top-right'
    | 'bottom-left'
    | 'bottom-right'
    | 'top-center'
    | 'bottom-center'
  richColors?: boolean
  closeButton?: boolean
  duration?: number
}

function Toaster({
  position = 'top-right',
  richColors = true,
  closeButton = true,
  duration = 4000,
}: ToasterProps = {}) {
  return (
    <SonnerToaster
      position={position}
      richColors={richColors}
      closeButton={closeButton}
      duration={duration}
      toastOptions={{
        classNames: {
          toast: 'font-sans',
          title: 'font-medium',
          description: 'text-sm',
        },
      }}
    />
  )
}

export { Toaster, toast }

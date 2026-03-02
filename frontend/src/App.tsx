/**
 * Componente raiz da aplicação HardwareMonitor.
 * Configura o roteamento React e gerencia a conexão WebSocket global.
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from '@/components/layout/Layout'
import Dashboard from '@/pages/Dashboard'
import FanProfiles from '@/pages/FanProfiles'
import Settings from '@/pages/Settings'
import { useHardwareStore } from '@/store/hardwareStore'

export default function App() {
  const connect = useHardwareStore((s) => s.connect)
  const disconnect = useHardwareStore((s) => s.disconnect)

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="fans" element={<FanProfiles />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

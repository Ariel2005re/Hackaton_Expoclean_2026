import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import NuevaCotizacion from './pages/NuevaCotizacion'
import Borradores from './pages/Borradores'
import Configuracion from './pages/Configuracion'
import Historial from './pages/Historial'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/nueva" replace />} />
        <Route path="nueva" element={<NuevaCotizacion />} />
        <Route path="borradores" element={<Borradores />} />
        <Route path="configuracion" element={<Configuracion />} />
        <Route path="historial" element={<Historial />} />
      </Route>
    </Routes>
  )
}

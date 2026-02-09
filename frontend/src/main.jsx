import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './improvements.css'       // 기본 UI 개선
import './premium-dynamic.css'    // 프리미엄 효과
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import '../src/assets/styles/typography.css';
import '../src/assets/styles/colors.css';
import '../src/assets/styles/iconSize.css';
import '../src/assets/styles/radius.css';
import '../src/assets/styles/spacing.css';
import '../src/assets/styles/effect.css';


createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

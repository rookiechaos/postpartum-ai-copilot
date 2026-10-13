import api from './api'

let activePrintCleanup = null

// Clone only the user-reviewed sheet. No new window, HTML interpolation or external service.
export function printView(elementId) {
  const source = document.getElementById(elementId)
  if (!source) throw new Error('Print sheet is unavailable')
  activePrintCleanup?.()
  document.querySelectorAll('.print-root').forEach(node => node.remove())
  const sheet = source.cloneNode(true)
  sheet.removeAttribute('id')
  sheet.classList.add('print-root')
  document.body.appendChild(sheet)
  document.body.dataset.printView = elementId
  let unsubscribe = () => {}
  const cleanup = () => {
    sheet.remove()
    if (activePrintCleanup === cleanup) {
      delete document.body.dataset.printView
      activePrintCleanup = null
    }
    window.removeEventListener('afterprint', cleanup)
    unsubscribe()
  }
  activePrintCleanup = cleanup
  unsubscribe = api.onAuthChange(({ preserveTasks }) => { if (!preserveTasks) cleanup() })
  window.addEventListener('afterprint', cleanup)
  try { window.print() } catch (error) { cleanup(); throw error }
}

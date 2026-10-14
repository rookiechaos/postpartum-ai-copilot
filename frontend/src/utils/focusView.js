// Reveal only in response to a user action; background refreshes must not move focus.
export function revealElement(element) {
  if (!element || element.closest('[hidden]') || element.disabled) return false
  let ancestor = element.parentElement
  while (ancestor) {
    if (ancestor.tagName === 'DETAILS') ancestor.open = true
    ancestor = ancestor.parentElement
  }
  element.scrollIntoView?.({ block: 'start', behavior: 'auto' })
  element.focus?.({ preventScroll: true })
  return element.ownerDocument.activeElement === element
}

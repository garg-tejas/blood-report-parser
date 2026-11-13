"use client"

import { useSyncExternalStore } from "react"

const mobileQuery = "(max-width: 767px)"
const serverSnapshot = () => false
const snapshot = () => window.matchMedia(mobileQuery).matches

function subscribe(onChange: () => void) {
  const query = window.matchMedia(mobileQuery)
  query.addEventListener("change", onChange)
  return () => query.removeEventListener("change", onChange)
}

export function useIsMobile() {
  return useSyncExternalStore(subscribe, snapshot, serverSnapshot)
}

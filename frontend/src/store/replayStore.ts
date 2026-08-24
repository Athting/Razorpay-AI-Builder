import { create } from 'zustand'

interface ReplayState {
  isRunning: boolean
  jobId: string | null
  total: number
  speed: number
  setRunning: (running: boolean, jobId?: string, total?: number) => void
  setSpeed: (speed: number) => void
  stop: () => void
}

export const useReplayStore = create<ReplayState>((set) => ({
  isRunning: false,
  jobId: null,
  total: 0,
  speed: 10,
  setRunning: (running, jobId, total) => set({ isRunning: running, jobId: jobId || null, total: total || 0 }),
  setSpeed: (speed) => set({ speed }),
  stop: () => set({ isRunning: false, jobId: null }),
}))

import { create } from "zustand";

export type ActivityStatus = "success" | "failed" | "info";

export interface Activity {
  id: string;
  type: string;
  title: string;
  detail: string;
  status: ActivityStatus;
  timestamp: string;
}

interface ActivityStore {
  activities: Activity[];
  addActivity: (entry: Omit<Activity, "id" | "timestamp">) => void;
  clearActivities: () => void;
}

export const useActivityStore = create<ActivityStore>((set) => ({
  activities: [],
  addActivity: (entry) => {
    set((s) => ({
      activities: [
        { ...entry, id: crypto.randomUUID(), timestamp: new Date().toISOString() },
        ...s.activities.slice(0, 199),
      ],
    }));
  },
  clearActivities: () => set({ activities: [] }),
}));

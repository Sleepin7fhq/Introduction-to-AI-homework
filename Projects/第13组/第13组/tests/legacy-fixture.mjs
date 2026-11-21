export function legacyFixture() {
  return {
    version: 1,
    revision: 8,
    plan: Array.from({ length: 7 }, () => ({ mode: "train", parts: ["胸"] })),
    goals: { weekly: 3, targetWeight: 65 },
    customExercises: [],
    workouts: [
      {
        id: "old-workout",
        date: "2026-01-01",
        status: "complete",
        createdAt: "2026-01-01T10:00:00Z",
        updatedAt: "2026-01-01T11:00:00Z",
        exercises: [
          {
            id: "old-entry",
            exerciseId: "bench",
            name: "杠铃卧推",
            part: "胸",
            loaded: true,
            sets: [{ id: "old-set", weight: 20, reps: 12 }],
          },
        ],
      },
      {
        id: "old-draft",
        date: "2026-01-02",
        status: "draft",
        createdAt: "2026-01-02T10:00:00Z",
        updatedAt: "2026-01-02T10:00:00Z",
        exercises: [],
      },
    ],
    weights: [
      {
        id: "old-weight",
        date: "2026-01-01",
        value: 70,
        createdAt: "2026-01-01T10:00:00Z",
        updatedAt: "2026-01-01T10:00:00Z",
      },
    ],
  };
}

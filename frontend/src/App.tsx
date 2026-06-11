import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { BottomNav } from "@/components/BottomNav";
import { ActiveSession } from "@/pages/ActiveSession";
import { ExerciseDetail } from "@/pages/ExerciseDetail";
import { Home } from "@/pages/Home";
import { Profile } from "@/pages/Profile";
import { SessionDetail } from "@/pages/SessionDetail";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="mx-auto min-h-dvh w-full max-w-md px-4 pb-28">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/session/active" element={<ActiveSession />} />
            <Route path="/session/:id" element={<SessionDetail />} />
            <Route path="/exercise/:id" element={<ExerciseDetail />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
        <BottomNav />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

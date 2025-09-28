import { Suspense } from "react";

import { SessionSidebar } from "@/components/session-sidebar";
import { SessionView } from "@/components/session-view";
import { Skeleton } from "@/components/ui/skeleton";
import { getSession, listSessions } from "@/lib/data";

type Props = {
  searchParams: { session?: string };
};

export default async function Home({ searchParams }: Props) {
  const sessions = await listSessions();

  if (sessions.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        No sessions found in ../documents
      </div>
    );
  }

  const activeId = searchParams.session ?? sessions[0].sessionId;
  const session = await getSession(activeId);

  return (
    <div className="flex min-h-screen">
      <SessionSidebar sessions={sessions} />
      <main className="flex-1 p-6">
        <Suspense fallback={<LoadingView />}>
          {session ? (
            <SessionView session={session} />
          ) : (
            <p className="text-sm text-muted-foreground">Unable to load session {activeId}</p>
          )}
        </Suspense>
      </main>
    </div>
  );
}

function LoadingView() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-6 w-48" />
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

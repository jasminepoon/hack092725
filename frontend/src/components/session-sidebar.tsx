"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

type SessionLink = {
  sessionId: string;
  createdAt?: string;
};

type Props = {
  sessions: SessionLink[];
};

export function SessionSidebar({ sessions }: Props) {
  const searchParams = useSearchParams();
  const active = searchParams.get("session") ?? sessions[0]?.sessionId;

  return (
    <aside className="w-64 border-r bg-background">
      <div className="p-4">
        <h2 className="text-sm font-semibold text-muted-foreground">Sessions</h2>
      </div>
      <ScrollArea className="h-[calc(100vh-4rem)]">
        <div className="space-y-2 p-4">
          {sessions.map(({ sessionId, createdAt }) => (
            <Button
              key={sessionId}
              variant={sessionId === active ? "secondary" : "ghost"}
              className="w-full justify-start text-left"
              asChild
            >
              <Link href={`/?session=${encodeURIComponent(sessionId)}`}>
                <div className="flex flex-col">
                  <span className="text-sm font-medium">{sessionId}</span>
                  {createdAt && (
                    <span className="text-xs text-muted-foreground">{createdAt}</span>
                  )}
                </div>
              </Link>
            </Button>
          ))}
        </div>
      </ScrollArea>
    </aside>
  );
}

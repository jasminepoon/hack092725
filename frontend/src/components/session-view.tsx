import { SessionDetail } from "@/lib/data";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type Props = {
  session: SessionDetail;
};

export function SessionView({ session }: Props) {
  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">{session.sessionId}</h1>
        {session.createdAt && (
          <Badge variant="outline" className="text-xs">
            {session.createdAt}
          </Badge>
        )}
      </header>

      {session.summary && (
        <Card>
          <CardHeader>
            <CardTitle>{session.summary.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {session.summary.sections.map((section) => (
              <div key={section.heading} className="space-y-2">
                <h3 className="text-sm font-semibold text-muted-foreground">{section.heading}</h3>
                <ul className="space-y-1 text-sm">
                  {section.bullets.map((bullet, idx) => (
                    <li key={idx} className="leading-relaxed">
                      - {bullet}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="turns">
        <TabsList>
          <TabsTrigger value="turns">Turn Log</TabsTrigger>
          <TabsTrigger value="augmentations">Augmentations</TabsTrigger>
        </TabsList>
        <TabsContent value="turns">
          <Card>
            <CardContent className="p-0">
              <ScrollArea className="h-[60vh]">
                <div className="divide-y">
                  {session.turns.map((turn) => (
                    <div key={turn.turn} className="p-4">
                      <div className="flex items-center gap-2 text-xs uppercase text-muted-foreground">
                        <span className="font-medium">Turn {turn.turn}</span>
                      </div>
                      <div className="mt-3 grid gap-3 md:grid-cols-2">
                        <div>
                          <h4 className="text-xs font-semibold text-muted-foreground">User</h4>
                          <p className="whitespace-pre-wrap text-sm">{turn.user ?? "—"}</p>
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold text-muted-foreground">Agent</h4>
                          <p className="whitespace-pre-wrap text-sm">{turn.agent ?? "—"}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="augmentations">
          <Card>
            <CardContent className="space-y-6 pt-6">
              {session.augmentations.length === 0 && (
                <p className="text-sm text-muted-foreground">No augmentations recorded.</p>
              )}
              {session.augmentations.map((entry) => (
                <div key={entry.turn} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold">Turn {entry.turn}</h4>
                    <Badge variant="outline">KE rewrite</Badge>
                  </div>
                  <div className="grid gap-3 md:grid-cols-3">
                    <Block label="Original" value={entry.original} />
                    <Block label="Suggestion" value={entry.suggestion} />
                    <Block label="Sent to Codex" value={entry.final} />
                  </div>
                  {entry.reasons.length > 0 && (
                    <div>
                      <Separator className="my-3" />
                      <h5 className="text-xs font-semibold text-muted-foreground">Why it changed</h5>
                      <ul className="mt-1 space-y-1 text-sm">
                        {entry.reasons.map((reason, idx) => (
                          <li key={idx}>- {reason}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Block({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border bg-muted/30 p-3">
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      <p className="mt-2 whitespace-pre-wrap text-sm">{value || "—"}</p>
    </div>
  );
}

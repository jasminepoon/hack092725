import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { NotebookPen, Wand2, Sparkles, Tags, ShieldCheck, GaugeCircle, History } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';

const Section = ({ title, icon: Icon, children, className, contentClassName }) => (
  <div className={cn('space-y-2', className)}>
    <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.25em] text-muted-foreground">
      {Icon ? <Icon size={14} className="text-primary" /> : null}
      {title}
    </div>
    <div className={cn('rounded-xl border border-border/70 bg-card/70 p-4 text-sm leading-relaxed shadow-[var(--shadow-sm)]', contentClassName)}>
      <pre className="whitespace-pre-wrap font-mono text-[13px] leading-relaxed text-foreground">
        {children}
      </pre>
    </div>
  </div>
);

const ToggleCard = ({ title, description, enabled, onToggle }) => (
  <button
    type="button"
    onClick={() => onToggle(!enabled)}
    className={cn(
      'flex w-full flex-col gap-3 rounded-2xl border px-5 py-4 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
      enabled
        ? 'border-primary/70 bg-primary/15 shadow-[var(--shadow-sm)]'
        : 'border-border/50 bg-transparent hover:bg-muted/20',
    )}
  >
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <span>{title}</span>
        <Badge className={enabled ? 'bg-primary text-primary-foreground shadow-[var(--shadow-sm)]' : 'border border-border bg-muted text-muted-foreground'}>
          {enabled ? 'Enabled' : 'Disabled'}
        </Badge>
      </div>
    </div>
    <p className="text-xs text-muted-foreground">{description}</p>
  </button>
);

export default function App() {
  const [sessionId, setSessionId] = useState('demo-session');
  const [question, setQuestion] = useState('');
  const [learnMode, setLearnMode] = useState(false);
  const [skipSynthesis, setSkipSynthesis] = useState(false);
  const [additionalGuidance, setAdditionalGuidance] = useState('');
  const [plan, setPlan] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionsError, setSessionsError] = useState('');

  const guardrails = result?.guardrail_feedback ?? [];
  const augmentation = result?.augmentation ?? null;
  const hasPlan = Boolean(plan);
  const hasAugmentation = Boolean(augmentation);
  const hasResult = Boolean(result);
  const [activeView, setActiveView] = useState('console');
  const [activeTab, setActiveTab] = useState(null);
  const planLoadedRef = useRef(false);
  const augmentationLoadedRef = useRef(false);
  const resultLoadedRef = useRef(false);

  const formatList = (items) => {
    if (!items?.length) return 'No justification provided.';
    return items.map((item) => `• ${item}`).join('\n');
  };

  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true);
    setSessionsError('');
    try {
      const response = await axios.get(`${API_BASE}/sessions`);
      setSessions(response.data ?? []);
    } catch (err) {
      setSessionsError(err.response?.data?.detail ?? err.message);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  useEffect(() => {
    if (activeView !== 'console') {
      return;
    }
    if (hasPlan && !planLoadedRef.current) {
      setActiveTab('plan');
      planLoadedRef.current = true;
    }
  }, [hasPlan, activeView]);

  useEffect(() => {
    if (activeView !== 'console') {
      return;
    }
    if (hasAugmentation && !augmentationLoadedRef.current) {
      setActiveTab('augmentation');
      augmentationLoadedRef.current = true;
    }
  }, [hasAugmentation, activeView]);

  useEffect(() => {
    if (activeView !== 'console') {
      return;
    }
    if (hasResult && !resultLoadedRef.current) {
      setActiveTab('outputs');
      resultLoadedRef.current = true;
    }
  }, [hasResult, activeView]);

  const visibleTabs = useMemo(
    () => {
      const tabs = [];
      if (hasPlan) tabs.push({ id: 'plan', label: 'Plan recap' });
      if (hasAugmentation) tabs.push({ id: 'augmentation', label: 'Prompt augmentation' });
      if (hasResult) tabs.push({ id: 'outputs', label: 'Run outputs' });
      return tabs;
    },
    [hasPlan, hasAugmentation, hasResult],
  );

  useEffect(() => {
    if (activeView !== 'console') {
      if (activeTab !== null) {
        setActiveTab(null);
      }
      return;
    }
    const available = visibleTabs.map((tab) => tab.id);
    if (!available.length) {
      if (activeTab !== null) {
        setActiveTab(null);
      }
      return;
    }
    if (!available.includes(activeTab)) {
      setActiveTab(available[available.length - 1]);
    }
  }, [visibleTabs, activeTab, activeView]);

  const resetOutputs = () => {
    setPlan(null);
    setResult(null);
    setError('');
    setAdditionalGuidance('');
    setActiveTab(null);
    planLoadedRef.current = false;
    augmentationLoadedRef.current = false;
    resultLoadedRef.current = false;
  };

  const handlePlan = async () => {
    setActiveView('console');
    setLoading(true);
    setError('');
    try {
      const response = await axios.post(`${API_BASE}/plan`, {
        session_id: sessionId,
        question,
      });
      setPlan(response.data);
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async (enforceLearnMode) => {
    setActiveView('console');
    setLoading(true);
    setError('');
    try {
      const response = await axios.post(`${API_BASE}/run`, {
        session_id: sessionId,
        question,
        learn_mode: learnMode && enforceLearnMode,
        skip_synthesis: skipSynthesis,
        extra_guidance: additionalGuidance.trim() || undefined,
      });
      setResult(response.data);
      await fetchSessions();
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    resetOutputs();

    if (!question.trim()) {
      setError('Please enter a question or task.');
      return;
    }

    if (learnMode) {
      await handlePlan();
      return;
    }

    await handleRun(false);
  };

  const executePlan = async () => {
    if (!plan) return;
    await handleRun(true);
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="relative isolate min-h-screen overflow-hidden">
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top,_oklch(0.93_0.03_262.4)_0%,_transparent_60%)]" />
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_bottom,_oklch(0.98_0.012_248.3)_0%,_transparent_65%)]" />

        <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-10 px-6 pb-16 pt-12">
          <header className="mx-auto max-w-2xl space-y-4 text-center">
            <Badge variant="secondary" className="mx-auto w-fit uppercase tracking-[0.4em]">
              Hack092725
            </Badge>
            <h1 className="text-4xl font-semibold tracking-tight lg:text-5xl">Agent Operations Console</h1>
            <p className="text-sm text-muted-foreground sm:text-base">
              Orchestrate the Task &amp; Knowledge Exchange agents, approve reuse plans, and capture reusable learnings—all from one panel.
            </p>
          </header>

          <div className="flex justify-center gap-3">
            <button
              type="button"
              onClick={() => setActiveView('console')}
              className={cn(
                'rounded-xl border px-5 py-2 text-sm font-semibold uppercase tracking-[0.3em] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                activeView === 'console'
                  ? 'border-primary bg-primary text-primary-foreground shadow-[var(--shadow-sm)]'
                  : 'border-border bg-background/70 text-muted-foreground hover:bg-muted/40',
              )}
            >
              Console
            </button>
            <button
              type="button"
              onClick={() => setActiveView('history')}
              className={cn(
                'rounded-xl border px-5 py-2 text-sm font-semibold uppercase tracking-[0.3em] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                activeView === 'history'
                  ? 'border-primary bg-primary text-primary-foreground shadow-[var(--shadow-sm)]'
                  : 'border-border bg-background/70 text-muted-foreground hover:bg-muted/40',
              )}
            >
              Session history
            </button>
          </div>

          {activeView === 'console' ? (
            <div className="flex flex-col items-center gap-6">
              <Card className="w-full max-w-3xl border-border/50 bg-card/80 shadow-[var(--shadow-lg)] backdrop-blur supports-[backdrop-filter]:backdrop-blur">
                <CardHeader className="space-y-2 text-center">
                  <CardTitle className="text-2xl font-semibold">Compose run</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Configure session memory and instructions before running the agents.
                  </p>
                </CardHeader>
                <CardContent className="space-y-4">
                  {error ? (
                    <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                      {error}
                    </div>
                  ) : null}

                  <form className="space-y-4" onSubmit={handleSubmit}>
                    <div className="space-y-2">
                      <Label htmlFor="session">Session ID</Label>
                      <Input
                        id="session"
                        value={sessionId}
                        onChange={(event) => setSessionId(event.target.value)}
                        placeholder="legal-saas"
                      />
                      <p className="text-xs text-muted-foreground">Memory persists per session identifier.</p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="question">Question / Task</Label>
                      <Textarea
                        id="question"
                        value={question}
                        onChange={(event) => setQuestion(event.target.value)}
                        placeholder="Ask the Task Agent..."
                        className="min-h-[150px]"
                      />
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                      <ToggleCard
                        title="Learn mode"
                        description="Preview prior solution and confirm before execution."
                        enabled={learnMode}
                        onToggle={(next) => {
                          setLearnMode(next);
                          resetOutputs();
                        }}
                      />
                      <ToggleCard
                        title="Skip KE synthesis"
                        description="Disable knowledge logging for dry runs."
                        enabled={skipSynthesis}
                        onToggle={setSkipSynthesis}
                      />
                    </div>

                    <Button type="submit" className="w-full" disabled={loading}>
                      {learnMode ? 'Generate recap' : 'Run Task Agent'}
                    </Button>
                  </form>
                </CardContent>
              </Card>

              <div className="w-full max-w-4xl space-y-6">
                {loading ? (
                  <Card className="border-border/50 bg-card/70 shadow-[var(--shadow-sm)] backdrop-blur supports-[backdrop-filter]:backdrop-blur">
                    <CardContent className="flex items-center gap-3 py-6 text-sm text-muted-foreground">
                      <Sparkles size={18} className="animate-pulse text-primary" />
                      Running agents… this may take a few seconds.
                    </CardContent>
                  </Card>
                ) : null}

                {visibleTabs.length ? (
                  <div className="space-y-4">
                    <div className="flex flex-wrap gap-2 rounded-2xl border border-border/60 bg-card/70 p-2 shadow-[var(--shadow-sm)]">
                      {visibleTabs.map((tab) => (
                        <button
                          key={tab.id}
                          type="button"
                          onClick={() => setActiveTab(tab.id)}
                          className={cn(
                            'rounded-xl px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                            activeTab === tab.id
                              ? 'bg-primary text-primary-foreground shadow-[var(--shadow-sm)]'
                              : 'bg-background/70 text-muted-foreground hover:bg-muted/40',
                          )}
                        >
                          {tab.label}
                        </button>
                      ))}
                    </div>

                    {activeTab === 'plan' && plan ? (
                      <Card className="border-border/40 bg-card/80 shadow-[var(--shadow-lg)] backdrop-blur supports-[backdrop-filter]:backdrop-blur">
                        <CardHeader className="space-y-3">
                          <Badge variant="secondary" className="w-fit uppercase tracking-[0.3em]">
                            Plan recap
                          </Badge>
                          <CardTitle className="text-2xl font-semibold">Review prior solution</CardTitle>
                          <p className="text-sm text-muted-foreground">
                            Inspect the cached solution and adapt before execution.
                          </p>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <Section title="Session digest" icon={Tags}>{plan.digest}</Section>
                          <Section title="Proposed plan" icon={NotebookPen}>{plan.plan_markdown}</Section>
                          <div className="space-y-2">
                            <Label htmlFor="guidance">Additional guidance</Label>
                            <Textarea
                              id="guidance"
                              placeholder="Tell the agent how to adapt the plan..."
                              value={additionalGuidance}
                              onChange={(event) => setAdditionalGuidance(event.target.value)}
                            />
                          </div>
                          <div className="flex flex-wrap items-center gap-3">
                            <Button onClick={executePlan} disabled={loading} className="min-w-[160px]">
                              Execute plan
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              disabled={loading}
                              onClick={() => {
                                setPlan(null);
                                setAdditionalGuidance('');
                                planLoadedRef.current = false;
                              }}
                            >
                              Cancel
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ) : null}

                    {activeTab === 'augmentation' && augmentation ? (
                    <Card className="border-border/40 bg-card/80 shadow-[var(--shadow-lg)] backdrop-blur supports-[backdrop-filter]:backdrop-blur">
                      <CardHeader className="space-y-3">
                        <Badge variant="secondary" className="w-fit uppercase tracking-[0.3em]">
                          Plan recap
                        </Badge>
                        <CardTitle className="text-2xl font-semibold">Review prior solution</CardTitle>
                        <p className="text-sm text-muted-foreground">
                          Inspect the cached solution and adapt before execution.
                        </p>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <Section title="Session digest" icon={Tags}>{plan.digest}</Section>
                        <Section title="Proposed plan" icon={NotebookPen}>{plan.plan_markdown}</Section>
                        <div className="space-y-2">
                          <Label htmlFor="guidance">Additional guidance</Label>
                          <Textarea
                            id="guidance"
                            placeholder="Tell the agent how to adapt the plan..."
                            value={additionalGuidance}
                            onChange={(event) => setAdditionalGuidance(event.target.value)}
                          />
                        </div>
                        <div className="flex flex-wrap items-center gap-3">
                          <Button onClick={executePlan} disabled={loading} className="min-w-[160px]">
                            Execute plan
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            disabled={loading}
                            onClick={() => {
                              setPlan(null);
                              setAdditionalGuidance('');
                              planLoadedRef.current = false;
                            }}
                          >
                            Cancel
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ) : null}

                  {activeTab === 'augmentation' && augmentation ? (
                    <Card className="border-primary/40 bg-card/80 shadow-[var(--shadow-lg)] backdrop-blur supports-[backdrop-filter]:backdrop-blur">
                      <CardHeader className="space-y-3">
                        <Badge variant="secondary" className="w-fit uppercase tracking-[0.3em]">
                          Prompt augmentation
                        </Badge>
                        <CardTitle className="text-2xl font-semibold">Review rewritten prompt</CardTitle>
                        <p className="text-sm text-muted-foreground">
                          Compare your original request against the suggestion sent to the Task Agent.
                        </p>
                      </CardHeader>
                      <CardContent className="grid gap-4 lg:grid-cols-2">
                        <Section title="Original prompt" icon={NotebookPen}>{augmentation.original}</Section>
                        <Section title="Augmented suggestion" icon={Sparkles}>{augmentation.suggestion}</Section>
                        <Section title="Final prompt sent" icon={Wand2}>{augmentation.final_prompt}</Section>
                        <Section title="Justification" icon={ShieldCheck}>{formatList(augmentation.justification)}</Section>
                        <Section title="Diff (original → suggestion)" icon={Sparkles} className="lg:col-span-2">
                          {augmentation.diff_original_suggestion?.trim()
                            ? augmentation.diff_original_suggestion
                            : 'No diff generated.'}
                        </Section>
                        {augmentation.final_prompt.trim() !== augmentation.suggestion.trim() ? (
                          <Section title="Diff (original → final)" icon={Sparkles} className="lg:col-span-2">
                            {augmentation.diff_original_final?.trim()
                              ? augmentation.diff_original_final
                              : 'No diff generated.'}
                          </Section>
                        ) : null}
                        {augmentation.raw_model_response?.trim() ? (
                          <Section title="Raw model response" icon={Tags} className="lg:col-span-2">
                            {augmentation.raw_model_response}
                          </Section>
                        ) : null}
                      </CardContent>
                    </Card>
                  ) : null}

                  {activeTab === 'outputs' && result ? (
                    <div className="grid gap-6 lg:grid-cols-2">
                      <Card className="border-border/40 bg-card/80 shadow-[var(--shadow-lg)] backdrop-blur supports-[backdrop-filter]:backdrop-blur">
                        <CardHeader>
                          <CardTitle className="text-2xl font-semibold">Task agent output</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <Section title="Response" icon={Wand2}>{result.final_output}</Section>
                          <Section title="Digest" icon={Tags}>{result.digest}</Section>
                        </CardContent>
                      </Card>

                      <Card className="border-border/40 bg-card/80 shadow-[var(--shadow-lg)] backdrop-blur supports-[backdrop-filter]:backdrop-blur">
                        <CardHeader>
                          <CardTitle className="text-2xl font-semibold">Session artefacts</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <Section title="Knowledge exchange summary" icon={Sparkles}>
                            {result.knowledge_exchange_summary ?? 'No updates logged in this run.'}
                          </Section>
                          <Section title="Guardrail feedback" icon={ShieldCheck}>
                            {guardrails.length ? guardrails.join('\n') : 'No guardrail notes.'}
                          </Section>
                          {result.usage ? (
                            <Section title="Usage" icon={GaugeCircle}>
                              Requests: {result.usage.requests}
                              {'\n'}Input tokens: {result.usage.input_tokens}
                              {'\n'}Output tokens: {result.usage.output_tokens}
                              {'\n'}Total tokens: {result.usage.total_tokens}
                            </Section>
                          ) : null}
                        </CardContent>
                      </Card>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          </div>
          ) : (
        <div className="mx-auto w-full max-w-4xl space-y-6">
          <Card className="border-border/40 bg-card/80 shadow-[var(--shadow-lg)] backdrop-blur supports-[backdrop-filter]:backdrop-blur">
            <CardHeader className="space-y-3">
              <Badge variant="secondary" className="w-fit uppercase tracking-[0.3em]">
                Previous sessions
              </Badge>
              <CardTitle className="text-2xl font-semibold">Session history</CardTitle>
              <p className="text-sm text-muted-foreground">
                Browse recent workstreams and switch the console context with a click.
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              {sessionsLoading ? (
                <div className="rounded-xl border border-border/60 bg-background/70 p-4 text-sm text-muted-foreground shadow-[var(--shadow-sm)]">
                  Loading recent sessions…
                </div>
              ) : sessionsError ? (
                <div className="rounded-xl border border-destructive/60 bg-destructive/10 p-4 text-sm text-destructive shadow-[var(--shadow-sm)]">
                  {sessionsError}
                </div>
              ) : sessions.length ? (
                <div className="grid gap-3">
                  {sessions.map((session) => (
                    <div
                      key={session.session_id}
                      className="rounded-2xl border border-border/50 bg-background/70 p-4 shadow-[var(--shadow-sm)]"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.3em] text-primary">
                            <History size={14} />
                            Session
                          </div>
                          <div className="text-lg font-semibold text-foreground">
                            {session.session_id}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Updated {new Date(session.updated_at).toLocaleString()}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSessionId(session.session_id);
                              resetOutputs();
                              setActiveView('console');
                            }}
                          >
                            Switch to session
                          </Button>
                        </div>
                      </div>
                      <div className="mt-3 grid gap-3 lg:grid-cols-2">
                        <Section
                          title="Digest"
                          icon={Tags}
                          className="lg:col-span-2"
                          contentClassName="bg-background"
                        >
                          {session.digest}
                        </Section>
                        {session.recent?.length ? (
                          <Section
                            title="Recent entries"
                            icon={Sparkles}
                            className="lg:col-span-2"
                            contentClassName="bg-background"
                          >
                            {session.recent
                              .map((item) => `(${item.kind}) ${item.summary}`)
                              .join('\n')}
                          </Section>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-border/60 bg-background/70 p-6 text-center text-sm text-muted-foreground shadow-[var(--shadow-sm)]">
                  No sessions logged yet. Run the agents to start capturing history.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </main>
  </div>
</div>
  );
}

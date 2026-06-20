import React, { useState } from "react";
import { 
  Beaker, 
  Droplets, 
  Activity, 
  Wind, 
  Layers, 
  Scissors, 
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Zap
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Label } from "../../ui/label";
import { Input } from "../../ui/input";
import { Slider } from "../../ui/slider";
import { Button } from "../../ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../ui/select";
import { Badge } from "../../ui/badge";

export function Dark() {
  const [formData, setFormData] = useState({
    shade: "Wella 7/1",
    gray_percentage: 25,
    starting_level: 6,
    texture: "medium",
    service_intent: "tone_deposit"
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch("http://localhost:5000/formula", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        throw new Error("Failed to fetch formulation");
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "An error occurred");
      // Fallback for mockup if actual API is not running
      setResult({
        status: "success",
        steps: [
          {
            step: 1,
            description: "Pre-lighten if necessary (skipped based on starting level)",
            action: "none"
          },
          {
            step: 2,
            description: "Apply base color",
            action: "mix",
            products: [
              { name: "Wella Koleston Perfect 7/1", amount: "45g" },
              { name: "Wella Koleston Perfect 7/0", amount: "15g (for gray coverage)" }
            ],
            developer: {
              name: "Wella Welloxon Perfect 20 Vol (6%)",
              amount: "60g"
            },
            ratio: "1:1"
          }
        ],
        warnings: [
          "Client has 25% gray. Base formula adjusted to include /0 series for optimal coverage."
        ]
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-[#e0e0e0] font-sans selection:bg-[#00f0ff] selection:text-black">
      {/* Self-contained dark theme overrides */}
      <style dangerouslySetInnerHTML={{ __html: `
        .dark-theme-override {
          --background: 240 10% 4%;
          --foreground: 0 0% 98%;
          --card: 240 10% 6%;
          --card-foreground: 0 0% 98%;
          --popover: 240 10% 6%;
          --popover-foreground: 0 0% 98%;
          --primary: 188 100% 50%;
          --primary-foreground: 240 5.9% 10%;
          --secondary: 240 10% 12%;
          --secondary-foreground: 0 0% 98%;
          --muted: 240 10% 12%;
          --muted-foreground: 240 5% 64.9%;
          --accent: 188 100% 50%;
          --accent-foreground: 240 5.9% 10%;
          --destructive: 0 84.2% 60.2%;
          --destructive-foreground: 0 0% 98%;
          --border: 240 10% 15%;
          --input: 240 10% 15%;
          --ring: 188 100% 50%;
          --radius: 0.25rem;
        }
        .glow-text {
          text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
        }
        .glow-border {
          box-shadow: 0 0 15px rgba(0, 240, 255, 0.15);
        }
        .cyber-panel {
          background: linear-gradient(135deg, rgba(20,20,24,1) 0%, rgba(10,10,12,1) 100%);
          border: 1px solid rgba(255,255,255,0.05);
        }
      `}} />

      <div className="dark-theme-override max-w-6xl mx-auto p-4 md:p-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Header */}
        <header className="lg:col-span-12 flex items-center justify-between border-b border-white/10 pb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded bg-[#00f0ff]/10 border border-[#00f0ff]/30 flex items-center justify-center">
              <Zap className="text-[#00f0ff] w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                COLOR<span className="text-[#00f0ff]">SYNTH</span>
                <Badge variant="outline" className="ml-2 border-[#00f0ff]/30 text-[#00f0ff] font-mono text-xs rounded-none bg-[#00f0ff]/5">v2.4.1</Badge>
              </h1>
              <p className="text-xs text-zinc-500 font-mono tracking-widest uppercase mt-1">Formulation Matrix Active</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4 text-xs font-mono text-zinc-400 bg-black/40 px-4 py-2 border border-white/5 rounded">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
              SYS: ONLINE
            </div>
            <div className="w-px h-4 bg-white/10"></div>
            <div>DB: SYNCED</div>
          </div>
        </header>

        {/* Left Column: Input Console */}
        <div className="lg:col-span-4 space-y-6">
          <Card className="bg-[#121214] border-white/10 rounded-sm overflow-hidden">
            <div className="h-1 w-full bg-gradient-to-r from-[#00f0ff] to-[#ff9900]"></div>
            <CardHeader className="pb-4">
              <CardTitle className="text-sm font-mono text-zinc-400 uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-[#00f0ff]" />
                Client Parameters
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                
                {/* Target Shade */}
                <div className="space-y-2">
                  <Label className="text-xs font-mono text-zinc-500 uppercase">Target Shade (TGT)</Label>
                  <div className="relative">
                    <Input 
                      value={formData.shade}
                      onChange={e => setFormData({...formData, shade: e.target.value})}
                      className="bg-black border-white/10 font-mono text-[#00f0ff] text-lg rounded-sm focus-visible:ring-[#00f0ff]/50 pl-10"
                      placeholder="e.g. Wella 7/1"
                    />
                    <Beaker className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                  </div>
                </div>

                {/* Current Level */}
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <Label className="text-xs font-mono text-zinc-500 uppercase">Current Level (LVL)</Label>
                    <span className="font-mono text-[#ff9900] bg-[#ff9900]/10 px-2 py-0.5 rounded text-xs">{formData.starting_level}</span>
                  </div>
                  <Input 
                    type="number"
                    min="1"
                    max="12"
                    value={formData.starting_level}
                    onChange={e => setFormData({...formData, starting_level: parseInt(e.target.value)})}
                    className="bg-black border-white/10 font-mono rounded-sm focus-visible:ring-[#ff9900]/50"
                  />
                </div>

                {/* Gray Percentage */}
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <Label className="text-xs font-mono text-zinc-500 uppercase">Gray Content (GRY)</Label>
                    <span className="font-mono text-white bg-white/10 px-2 py-0.5 rounded text-xs">{formData.gray_percentage}%</span>
                  </div>
                  <Slider 
                    value={[formData.gray_percentage]}
                    onValueChange={([val]) => setFormData({...formData, gray_percentage: val})}
                    max={100}
                    step={5}
                    className="py-2"
                  />
                  <div className="flex justify-between text-[10px] font-mono text-zinc-600">
                    <span>0%</span>
                    <span>50%</span>
                    <span>100%</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {/* Texture */}
                  <div className="space-y-2">
                    <Label className="text-xs font-mono text-zinc-500 uppercase">Texture</Label>
                    <Select 
                      value={formData.texture} 
                      onValueChange={(val) => setFormData({...formData, texture: val})}
                    >
                      <SelectTrigger className="bg-black border-white/10 font-mono text-xs rounded-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-[#121214] border-white/10 rounded-sm">
                        <SelectItem value="fine" className="font-mono text-xs focus:bg-white/5">Fine</SelectItem>
                        <SelectItem value="medium" className="font-mono text-xs focus:bg-white/5">Medium</SelectItem>
                        <SelectItem value="coarse" className="font-mono text-xs focus:bg-white/5">Coarse</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Intent */}
                  <div className="space-y-2">
                    <Label className="text-xs font-mono text-zinc-500 uppercase">Intent</Label>
                    <Select 
                      value={formData.service_intent} 
                      onValueChange={(val) => setFormData({...formData, service_intent: val})}
                    >
                      <SelectTrigger className="bg-black border-white/10 font-mono text-xs rounded-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-[#121214] border-white/10 rounded-sm">
                        <SelectItem value="tone_deposit" className="font-mono text-xs focus:bg-white/5">Tone/Deposit</SelectItem>
                        <SelectItem value="lift_deposit" className="font-mono text-xs focus:bg-white/5">Lift+Deposit</SelectItem>
                        <SelectItem value="gray_coverage" className="font-mono text-xs focus:bg-white/5">Gray Cov</SelectItem>
                        <SelectItem value="corrective" className="font-mono text-xs focus:bg-white/5">Corrective</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <Button 
                  type="submit" 
                  className="w-full bg-[#00f0ff] hover:bg-[#00c0cc] text-black font-bold tracking-wider rounded-sm h-12 uppercase group transition-all"
                  disabled={loading}
                >
                  {loading ? (
                    <span className="flex items-center gap-2 font-mono">
                      <Zap className="w-4 h-4 animate-spin" /> SYNTHESIZING...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <Layers className="w-4 h-4" /> COMPUTE FORMULA
                      <ChevronRight className="w-4 h-4 ml-auto opacity-50 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                    </span>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Output Display */}
        <div className="lg:col-span-8">
          <div className="h-full flex flex-col gap-6">
            
            {/* Status Bar */}
            <div className="flex items-center justify-between p-3 bg-[#121214] border border-white/10 rounded-sm">
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${result ? 'bg-[#00f0ff] glow-border' : 'bg-zinc-600'}`}></div>
                <span className="text-xs font-mono text-zinc-400">PRESCRIPTION STATUS</span>
              </div>
              <div className="text-xs font-mono">
                {loading ? <span className="text-zinc-500">PROCESSING_</span> : result ? <span className="text-[#00f0ff]">READY</span> : <span className="text-zinc-600">IDLE</span>}
              </div>
            </div>

            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-sm flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-red-500 uppercase mb-1">Computation Error</h4>
                  <p className="text-xs text-red-400/80 font-mono">{error}</p>
                </div>
              </div>
            )}

            {!result && !loading && !error && (
              <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-white/10 rounded-sm p-12 text-center bg-black/20">
                <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4 border border-white/5">
                  <Beaker className="w-8 h-8 text-zinc-600" />
                </div>
                <h3 className="text-lg font-mono text-zinc-400 mb-2">AWAITING INPUT</h3>
                <p className="text-sm text-zinc-600 max-w-sm">Enter client parameters in the matrix to generate a precise chemical formulation.</p>
              </div>
            )}

            {result && (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                
                {/* Result Highlights */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-[#121214] border border-white/10 p-4 rounded-sm border-l-2 border-l-[#00f0ff]">
                    <div className="text-[10px] font-mono text-zinc-500 mb-1">PRIMARY SHADE</div>
                    <div className="text-xl font-mono text-white glow-text">{formData.shade}</div>
                  </div>
                  <div className="bg-[#121214] border border-white/10 p-4 rounded-sm border-l-2 border-l-[#ff9900]">
                    <div className="text-[10px] font-mono text-zinc-500 mb-1">DEVELOPER STRENGTH</div>
                    <div className="text-xl font-mono text-white">20 VOL <span className="text-zinc-500 text-sm">6%</span></div>
                  </div>
                  <div className="bg-[#121214] border border-white/10 p-4 rounded-sm border-l-2 border-l-white/20">
                    <div className="text-[10px] font-mono text-zinc-500 mb-1">MIX RATIO</div>
                    <div className="text-xl font-mono text-white">1:1</div>
                  </div>
                </div>

                {/* Steps */}
                <Card className="bg-[#121214] border-white/10 rounded-sm">
                  <CardHeader className="border-b border-white/5 pb-4">
                    <CardTitle className="text-sm font-mono text-zinc-400 uppercase tracking-wider flex items-center gap-2">
                      <Scissors className="w-4 h-4 text-[#00f0ff]" />
                      Execution Protocol
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="divide-y divide-white/5">
                      {result.steps?.map((step: any, idx: number) => (
                        <div key={idx} className="p-6 hover:bg-white/[0.02] transition-colors">
                          <div className="flex items-start gap-4">
                            <div className="w-8 h-8 shrink-0 rounded bg-white/5 border border-white/10 flex items-center justify-center font-mono text-xs text-zinc-400">
                              0{step.step}
                            </div>
                            <div className="flex-1 space-y-4">
                              <h4 className="text-sm font-medium text-white">{step.description}</h4>
                              
                              {step.action === 'mix' && step.products && (
                                <div className="bg-black/50 border border-white/5 rounded p-4 font-mono text-sm space-y-3">
                                  {step.products.map((p: any, i: number) => (
                                    <div key={i} className="flex justify-between items-center pb-2 border-b border-dashed border-white/10 last:border-0 last:pb-0">
                                      <span className="text-[#00f0ff]">{p.name}</span>
                                      <span className="text-white">{p.amount}</span>
                                    </div>
                                  ))}
                                  {step.developer && (
                                    <div className="flex justify-between items-center pt-2 border-t border-solid border-white/10">
                                      <span className="text-zinc-400 flex items-center gap-2">
                                        <Droplets className="w-3 h-3" />
                                        {step.developer.name}
                                      </span>
                                      <span className="text-white">{step.developer.amount}</span>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Warnings / Insights */}
                {result.warnings && result.warnings.length > 0 && (
                  <div className="bg-[#ff9900]/10 border border-[#ff9900]/20 rounded-sm p-4">
                    <h4 className="text-[10px] font-mono text-[#ff9900] uppercase tracking-wider mb-3 flex items-center gap-2">
                      <AlertCircle className="w-3 h-3" /> System Diagnostics
                    </h4>
                    <ul className="space-y-2">
                      {result.warnings.map((warn: string, i: number) => (
                        <li key={i} className="text-sm text-zinc-300 flex items-start gap-2">
                          <span className="text-[#ff9900] mt-1">-</span>
                          {warn}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { Beaker, AlertCircle, Droplets, Activity, Loader2, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';

export function Clean() {
  const [isReady, setIsReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  // Form State
  const [targetShade, setTargetShade] = useState('Wella 7/1');
  const [grayPercentage, setGrayPercentage] = useState([0]);
  const [currentLevel, setCurrentLevel] = useState('5');
  const [hairTexture, setHairTexture] = useState('medium');
  const [serviceIntent, setServiceIntent] = useState('tone_deposit');

  // Check API health
  useEffect(() => {
    fetch('http://localhost:5000/health')
      .then(res => setIsReady(res.ok))
      .catch(() => setIsReady(false));
  }, []);

  const handleBuildFormula = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const payload = {
      target_shade: targetShade,
      current_level: parseInt(currentLevel, 10),
      gray_percentage: grayPercentage[0],
      hair_texture: hairTexture,
      service_intent: serviceIntent,
    };

    try {
      const response = await fetch('http://localhost:5000/formula', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Failed to generate formula. The API may be unavailable or returned an error.');
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred.');
      // Provide fallback mock data for preview purposes
      setTimeout(() => {
        setResult({
          formula_steps: [
            {
              step_number: 1,
              action: "Pre-lighten",
              description: "Lighten to pale yellow (level 9) if required, depending on starting level."
            },
            {
              step_number: 2,
              action: "Apply Color",
              description: `Mix 1 part ${targetShade} with 1 part developer.`
            }
          ],
          recommendations: {
            developer: "20 Volume (6%)",
            processing_time: "35-45 minutes",
            notes: `Adjust developer if lifting more than 2 levels. Hair texture is ${hairTexture}, monitor processing.`
          }
        });
        setError("API unavailable. Showing sample formula data.");
        setLoading(false);
      }, 1000);
      return;
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900">
      <style dangerouslySetInnerHTML={{__html: `
        :root {
          --radius: 0.3rem;
        }
      `}} />
      
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="bg-slate-900 text-white p-2 rounded-md">
            <Beaker className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-slate-900 leading-none">Formulation Engine</h1>
            <p className="text-xs text-slate-500 mt-1 font-medium">CLINICAL PRECISION</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-600 bg-slate-100 px-3 py-1.5 rounded-full">
            <span className={\`w-2 h-2 rounded-full \${isReady ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'}\`}></span>
            {isReady ? 'API Ready' : 'Connecting...'}
          </div>
        </div>
      </header>

      {/* Main Layout */}
      <main className="flex-1 max-w-[1400px] w-full mx-auto grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-6 p-6">
        
        {/* Left Column: Input Form */}
        <div className="flex flex-col gap-6">
          <Card className="border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden">
            <CardHeader className="bg-slate-50/50 border-b border-slate-100 pb-4">
              <CardTitle className="text-base font-semibold text-slate-800 flex items-center gap-2">
                <Activity className="w-4 h-4 text-slate-400" />
                Client Parameters
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <form onSubmit={handleBuildFormula} className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="shade" className="text-xs font-semibold uppercase tracking-wider text-slate-500">Target Shade</Label>
                  <Input 
                    id="shade" 
                    value={targetShade}
                    onChange={(e) => setTargetShade(e.target.value)}
                    className="font-mono text-sm bg-slate-50 focus-visible:ring-slate-400"
                    placeholder="e.g. Wella 7/1"
                  />
                  <p className="text-[11px] text-slate-400">Standard nomenclature (Brand Level/Tone)</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="level" className="text-xs font-semibold uppercase tracking-wider text-slate-500">Current Level</Label>
                    <Select value={currentLevel} onValueChange={setCurrentLevel}>
                      <SelectTrigger className="bg-slate-50">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {[...Array(12)].map((_, i) => (
                          <SelectItem key={i+1} value={(i+1).toString()}>Level {i+1}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="texture" className="text-xs font-semibold uppercase tracking-wider text-slate-500">Hair Texture</Label>
                    <Select value={hairTexture} onValueChange={setHairTexture}>
                      <SelectTrigger className="bg-slate-50">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="fine">Fine</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="coarse">Coarse</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-4 pt-2">
                  <div className="flex items-center justify-between">
                    <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Gray Percentage</Label>
                    <span className="text-sm font-mono text-slate-700 bg-slate-100 px-2 py-0.5 rounded">{grayPercentage}%</span>
                  </div>
                  <Slider 
                    value={grayPercentage} 
                    onValueChange={setGrayPercentage} 
                    max={100} 
                    step={5}
                    className="py-2"
                  />
                </div>

                <div className="space-y-2 pt-2">
                  <Label htmlFor="intent" className="text-xs font-semibold uppercase tracking-wider text-slate-500">Service Intent</Label>
                  <Select value={serviceIntent} onValueChange={setServiceIntent}>
                    <SelectTrigger className="bg-slate-50">
                      <SelectValue placeholder="Select service" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="tone_deposit">Tone & Deposit</SelectItem>
                      <SelectItem value="lift_deposit">Lift & Deposit</SelectItem>
                      <SelectItem value="gray_coverage">Gray Coverage</SelectItem>
                      <SelectItem value="color_correction">Color Correction</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Button 
                  type="submit" 
                  disabled={loading}
                  className="w-full bg-slate-900 hover:bg-slate-800 text-white font-medium h-11"
                >
                  {loading ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Computing...</>
                  ) : (
                    <>Build Formula <ArrowRight className="w-4 h-4 ml-2" /></>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Results */}
        <div className="flex flex-col h-[calc(100vh-8rem)]">
          {error && (
            <div className="mb-4 bg-amber-50 text-amber-800 p-4 rounded-lg border border-amber-200 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
              <div className="text-sm">{error}</div>
            </div>
          )}

          <Card className="flex-1 border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden flex flex-col">
            <CardHeader className="bg-slate-50/50 border-b border-slate-100">
              <CardTitle className="text-base font-semibold text-slate-800 flex items-center gap-2">
                <Droplets className="w-4 h-4 text-slate-400" />
                Formulation Prescription
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0 flex-1 relative">
              <ScrollArea className="h-full absolute inset-0">
                <div className="p-8">
                  {!result && !loading && (
                    <div className="flex flex-col items-center justify-center h-64 text-center">
                      <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                        <Beaker className="w-6 h-6 text-slate-300" />
                      </div>
                      <h3 className="text-lg font-medium text-slate-900 mb-1">Awaiting Parameters</h3>
                      <p className="text-sm text-slate-500 max-w-sm">Enter client details and target shade to generate a precise formulation.</p>
                    </div>
                  )}

                  {loading && !result && (
                    <div className="flex flex-col items-center justify-center h-64 text-center">
                      <Loader2 className="w-8 h-8 text-slate-400 animate-spin mb-4" />
                      <p className="text-sm text-slate-500">Analyzing compatibility and calculating ratios...</p>
                    </div>
                  )}

                  {result && (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out space-y-10">
                      
                      {/* Formula Steps */}
                      <div>
                        <h3 className="text-sm font-semibold uppercase tracking-widest text-slate-400 mb-6 flex items-center">
                          <span className="w-6 border-b border-slate-200 mr-3"></span>
                          Action Plan
                        </h3>
                        <div className="space-y-6">
                          {result.formula_steps?.map((step: any, idx: number) => (
                            <div key={idx} className="flex gap-4">
                              <div className="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center font-mono text-sm shrink-0 mt-0.5">
                                {step.step_number || (idx + 1)}
                              </div>
                              <div>
                                <h4 className="text-base font-medium text-slate-900 mb-1">{step.action}</h4>
                                <p className="text-slate-600 text-sm leading-relaxed">{step.description}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      <Separator className="bg-slate-100" />

                      {/* Developer & Processing */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-slate-50 rounded-xl p-5 border border-slate-100">
                          <h4 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">Developer</h4>
                          <div className="text-lg font-medium text-slate-900">
                            {result.recommendations?.developer || "Standard"}
                          </div>
                        </div>
                        <div className="bg-slate-50 rounded-xl p-5 border border-slate-100">
                          <h4 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">Processing Time</h4>
                          <div className="text-lg font-medium text-slate-900">
                            {result.recommendations?.processing_time || "Check visually"}
                          </div>
                        </div>
                      </div>

                      {/* Clinical Notes */}
                      {result.recommendations?.notes && (
                        <div className="bg-blue-50/50 border border-blue-100 rounded-xl p-5 text-blue-900">
                          <h4 className="text-xs font-semibold uppercase tracking-widest text-blue-500/70 mb-2">Clinical Notes</h4>
                          <p className="text-sm leading-relaxed">{result.recommendations.notes}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}

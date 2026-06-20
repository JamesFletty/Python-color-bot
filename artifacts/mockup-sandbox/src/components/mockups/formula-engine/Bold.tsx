import React, { useState } from 'react';
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Beaker, Sparkles, Droplet, AlertCircle, RefreshCcw } from 'lucide-react';
import { cn } from "@/lib/utils";

export function Bold() {
  const [formData, setFormData] = useState({
    target_shade: "Wella 7/1",
    gray_percentage: [0],
    current_level: "7",
    hair_texture: "medium",
    service_intent: "tone_deposit"
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const payload = {
        target_shade: formData.target_shade,
        gray_percentage: formData.gray_percentage[0],
        starting_level: parseInt(formData.current_level),
        texture: formData.hair_texture,
        service_intent: formData.service_intent
      };

      const res = await fetch('http://localhost:5000/formula', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error('Failed to fetch formula. Please try again.');
      }

      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'An error occurred while building the formula.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div 
      className="min-h-screen font-serif flex flex-col"
      style={{
        backgroundColor: '#1a0b12',
        color: '#fdf8fa',
        '--radius': '0rem'
      } as React.CSSProperties}
    >
      <style dangerouslySetInnerHTML={{__html: `
        .luxury-input {
          background-color: transparent !important;
          border: none !important;
          border-bottom: 2px solid #5a2e3d !important;
          border-radius: 0 !important;
          padding-left: 0 !important;
          padding-right: 0 !important;
          font-size: 1.25rem !important;
          color: #fdf8fa !important;
          transition: border-color 0.3s ease !important;
          box-shadow: none !important;
        }
        .luxury-input:focus {
          border-bottom-color: #d4af37 !important;
          outline: none !important;
        }
        .luxury-button {
          background-color: #5a2e3d;
          color: #fdf8fa;
          transition: all 0.3s ease;
          border: 1px solid transparent;
        }
        .luxury-button:hover {
          background-color: transparent;
          border-color: #d4af37;
          color: #d4af37;
        }
        .luxury-card {
          background-color: #241118 !important;
          border: 1px solid #3a1e27 !important;
          border-radius: 0 !important;
        }
      `}} />

      {/* Hero Header */}
      <header className="pt-24 pb-16 px-8 text-center border-b border-[#3a1e27]">
        <h1 className="text-6xl tracking-widest uppercase font-light text-[#d4af37] mb-4">
          L'Atelier
        </h1>
        <p className="text-xl text-[#b895a1] tracking-wide font-sans font-light max-w-2xl mx-auto">
          Precise formulation engineering for master colorists.
        </p>
      </header>

      <main className="flex-1 w-full max-w-4xl mx-auto px-6 py-12">
        <form onSubmit={handleSubmit} className="space-y-16">
          
          <div className="space-y-4">
            <Label className="text-sm tracking-widest uppercase text-[#b895a1]">Target Shade</Label>
            <Input 
              className="luxury-input h-14" 
              placeholder="e.g. Wella 7/1"
              value={formData.target_shade}
              onChange={e => setFormData({...formData, target_shade: e.target.value})}
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
            <div className="space-y-6">
              <Label className="text-sm tracking-widest uppercase text-[#b895a1] flex justify-between">
                <span>Gray Percentage</span>
                <span className="text-[#d4af37]">{formData.gray_percentage[0]}%</span>
              </Label>
              <Slider 
                min={0} max={100} step={5}
                value={formData.gray_percentage}
                onValueChange={v => setFormData({...formData, gray_percentage: v})}
                className="py-4"
              />
            </div>

            <div className="space-y-4">
              <Label className="text-sm tracking-widest uppercase text-[#b895a1]">Current Level</Label>
              <Select 
                value={formData.current_level} 
                onValueChange={v => setFormData({...formData, current_level: v})}
              >
                <SelectTrigger className="luxury-input h-14">
                  <SelectValue placeholder="Select level" />
                </SelectTrigger>
                <SelectContent className="bg-[#241118] border-[#3a1e27] text-[#fdf8fa] rounded-none">
                  {[...Array(12)].map((_, i) => (
                    <SelectItem key={i+1} value={(i+1).toString()} className="focus:bg-[#3a1e27] focus:text-[#d4af37]">
                      Level {i+1}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
            <div className="space-y-4">
              <Label className="text-sm tracking-widest uppercase text-[#b895a1]">Hair Texture</Label>
              <Select 
                value={formData.hair_texture} 
                onValueChange={v => setFormData({...formData, hair_texture: v})}
              >
                <SelectTrigger className="luxury-input h-14">
                  <SelectValue placeholder="Select texture" />
                </SelectTrigger>
                <SelectContent className="bg-[#241118] border-[#3a1e27] text-[#fdf8fa] rounded-none">
                  <SelectItem value="fine" className="focus:bg-[#3a1e27] focus:text-[#d4af37]">Fine</SelectItem>
                  <SelectItem value="medium" className="focus:bg-[#3a1e27] focus:text-[#d4af37]">Medium</SelectItem>
                  <SelectItem value="coarse" className="focus:bg-[#3a1e27] focus:text-[#d4af37]">Coarse</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-4">
              <Label className="text-sm tracking-widest uppercase text-[#b895a1]">Service Intent</Label>
              <Select 
                value={formData.service_intent} 
                onValueChange={v => setFormData({...formData, service_intent: v})}
              >
                <SelectTrigger className="luxury-input h-14">
                  <SelectValue placeholder="Select service" />
                </SelectTrigger>
                <SelectContent className="bg-[#241118] border-[#3a1e27] text-[#fdf8fa] rounded-none">
                  <SelectItem value="tone_deposit" className="focus:bg-[#3a1e27] focus:text-[#d4af37]">Tone / Deposit</SelectItem>
                  <SelectItem value="lift_deposit" className="focus:bg-[#3a1e27] focus:text-[#d4af37]">Lift & Deposit</SelectItem>
                  <SelectItem value="gray_coverage" className="focus:bg-[#3a1e27] focus:text-[#d4af37]">Gray Coverage</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button 
            type="submit" 
            className="w-full h-16 text-lg tracking-[0.2em] uppercase font-sans luxury-button"
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="flex items-center gap-3">
                <Loader2 className="w-5 h-5 animate-spin text-[#d4af37]" />
                Formulating...
              </span>
            ) : (
              <span className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-[#d4af37]" />
                Build Formula
              </span>
            )}
          </Button>
        </form>

        {/* Status Indicator */}
        <div className="mt-8 flex justify-center items-center gap-2 text-xs uppercase tracking-widest font-sans text-[#b895a1]">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          Engine Online
        </div>

        {/* Results Area */}
        {error && (
          <div className="mt-16 p-6 border border-red-900/50 bg-red-950/20 text-red-200 flex items-start gap-4">
            <AlertCircle className="w-6 h-6 shrink-0 text-red-500" />
            <p className="font-sans leading-relaxed">{error}</p>
          </div>
        )}

        {result && (
          <div className="mt-20 space-y-12 animate-in fade-in slide-in-from-bottom-8 duration-700">
            <div className="text-center">
              <h2 className="text-3xl tracking-widest uppercase font-light text-[#d4af37] mb-2">Prescription</h2>
              <p className="text-[#b895a1] font-sans">Tailored for {formData.target_shade}</p>
            </div>

            {/* Simulated Swatch */}
            <div className="flex justify-center">
              <div className="w-32 h-32 rounded-full border-4 border-[#3a1e27] shadow-2xl relative overflow-hidden flex items-center justify-center bg-gradient-to-br from-[#8a7251] to-[#3d2e1b]">
                <div className="absolute inset-0 bg-black/20 mix-blend-overlay"></div>
                <span className="relative z-10 font-sans tracking-widest text-sm text-white/80">TARGET</span>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6">
              {result.steps ? result.steps.map((step: any, idx: number) => (
                <Card key={idx} className="luxury-card">
                  <CardHeader className="pb-3 border-b border-[#3a1e27]">
                    <CardTitle className="text-lg font-light tracking-widest uppercase text-[#d4af37] flex items-center gap-3">
                      <Beaker className="w-5 h-5" />
                      Step {idx + 1}: {step.type || 'Mix'}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-6 font-sans">
                    <ul className="space-y-4">
                      {step.products?.map((prod: any, i: number) => (
                        <li key={i} className="flex justify-between items-center text-lg">
                          <span className="text-[#fdf8fa]">{prod.name}</span>
                          <span className="text-[#b895a1] font-mono bg-[#1a0b12] px-3 py-1 border border-[#3a1e27]">{prod.amount}g</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )) : (
                <Card className="luxury-card">
                  <CardHeader className="pb-3 border-b border-[#3a1e27]">
                    <CardTitle className="text-lg font-light tracking-widest uppercase text-[#d4af37] flex items-center gap-3">
                      <Droplet className="w-5 h-5" />
                      Suggested Mix
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-6 font-sans">
                    <pre className="text-sm text-[#b895a1] whitespace-pre-wrap font-mono">
                      {JSON.stringify(result, null, 2)}
                    </pre>
                  </CardContent>
                </Card>
              )}
            </div>

            <div className="flex justify-center pt-8 border-t border-[#3a1e27]">
              <Button variant="ghost" className="text-[#b895a1] hover:text-[#d4af37] hover:bg-transparent font-sans tracking-widest uppercase text-sm flex items-center gap-2" onClick={() => setResult(null)}>
                <RefreshCcw className="w-4 h-4" />
                Start Over
              </Button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { Brain, Server, Database, Chrome, Smartphone, HardDrive, Cloud, ArrowRight, Camera, MessageSquare, MapPin, CreditCard, Check, Sparkles, ChevronRight, Users, MessageCircle, Clock, Calendar, CheckCircle } from 'lucide-react';

const iOS2AndroidArchitectureViz = () => {
  const [stage, setStage] = useState(0);
  const maxStages = 5;

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.key === 'ArrowRight' && stage < maxStages) {
        setStage(prev => Math.min(prev + 1, maxStages));
      } else if (e.key === 'ArrowLeft' && stage > 0) {
        setStage(prev => Math.max(prev - 1, 0));
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [stage]);

  return (
    <div className="w-full min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-green-50 p-12">
      {/* Title */}
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold mb-4">
          <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-green-600 bg-clip-text text-transparent">
            iOS2Android Migration Agent Architecture
          </span>
        </h1>
        <p className="text-2xl text-gray-700 max-w-5xl mx-auto">
          AI orchestrating device transitions through natural conversation while preserving family connections
        </p>
      </div>

      {/* Main Architecture Flow - Three Columns */}
      <div className="max-w-[1400px] mx-auto mb-12">
        <div className="flex items-center justify-between gap-8">
          
          {/* Column 1: Claude Desktop */}
          <div className={`flex-1 flex justify-center transition-all duration-700 ${stage >= 1 ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-10'}`}>
            <div className="bg-white rounded-2xl p-6 shadow-xl border-2 border-blue-300 w-[320px]">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                  <Brain className="w-8 h-8 text-white" />
                </div>
                <div>
                  <h3 className="text-3xl font-bold text-blue-800">Claude Desktop</h3>
                  <p className="text-base text-gray-600">Mac Environment</p>
                </div>
              </div>
              
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4 border border-blue-200 mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="w-5 h-5 text-purple-600" />
                  <span className="text-lg font-semibold text-purple-700">iOS2Android Agent</span>
                </div>
                <p className="text-base text-gray-600">Natural Language AI Orchestrator</p>
              </div>
              
              <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-3 text-sm text-white font-semibold text-center">
                <p>Powered by Claude Opus 4</p>
              </div>
            </div>
          </div>

          {/* Arrow 1 */}
          <div className={`flex items-center transition-all duration-500 ${stage >= 2 ? 'opacity-100' : 'opacity-0'}`}>
            <div className="flex flex-col items-center">
              <ArrowRight className="w-12 h-12 text-gray-400" />
              <p className="text-sm text-gray-600 mt-2 font-semibold">MCP<br/>Protocol</p>
            </div>
          </div>

          {/* Column 2: MCP Servers Container */}
          <div className={`flex-1 flex justify-center transition-all duration-700 ${stage >= 2 ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-10'}`}>
            <div className="bg-white/50 rounded-2xl p-6 border-2 border-purple-300">
              <div className="flex items-center gap-2 mb-4">
                <Server className="w-6 h-6 text-purple-600" />
                <h3 className="text-2xl font-bold text-purple-800">MCP Servers</h3>
              </div>
              <p className="text-sm text-gray-600 text-center mb-4">Tool Orchestration Layer</p>
              
              <div className={`flex flex-col gap-4 transition-all duration-700 ${stage >= 3 ? 'opacity-100' : 'opacity-0'}`}>
                {/* Web Automation Server */}
                <div className="bg-gradient-to-r from-orange-100 to-amber-100 rounded-xl p-4 shadow-lg border-2 border-orange-300">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-10 h-10 bg-orange-500 rounded-full flex items-center justify-center">
                      <Chrome className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h4 className="text-xl font-bold text-orange-800">Web-Automation</h4>
                      <p className="text-sm text-gray-600">Playwright (4 tools)</p>
                    </div>
                  </div>
                  <div className="text-sm space-y-1 text-gray-700 pl-2">
                    <p>• iCloud status check</p>
                    <p>• Photo transfer initiation</p>
                    <p>• Google One monitoring</p>
                  </div>
                </div>

                {/* Mobile MCP Server */}
                <div className="bg-gradient-to-r from-green-100 to-emerald-100 rounded-xl p-4 shadow-lg border-2 border-green-300">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center">
                      <Smartphone className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h4 className="text-xl font-bold text-green-800">Mobile-MCP</h4>
                      <p className="text-sm text-gray-600">ADB Control (Natural Lang)</p>
                    </div>
                  </div>
                  <div className="text-sm space-y-1 text-gray-700 pl-2">
                    <p>• WhatsApp group creation</p>
                    <p>• Google Maps family setup</p>
                    <p>• Venmo teen activation</p>
                  </div>
                </div>

                {/* Migration State Server */}
                <div className="bg-gradient-to-r from-blue-100 to-cyan-100 rounded-xl p-4 shadow-lg border-2 border-blue-300">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
                      <Database className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h4 className="text-xl font-bold text-blue-800">Migration-State</h4>
                      <p className="text-sm text-gray-600">DuckDB Mgmt (7 tools)</p>
                    </div>
                  </div>
                  <div className="text-sm space-y-1 text-gray-700 pl-2">
                    <p>• Migration lifecycle tracking</p>
                    <p>• Family member coordination</p>
                    <p>• Progress calculation</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Arrow 2 */}
          <div className={`flex items-center transition-all duration-500 ${stage >= 4 ? 'opacity-100' : 'opacity-0'}`}>
            <div className="flex flex-col items-center">
              <ArrowRight className="w-12 h-12 text-gray-400" />
              <p className="text-sm text-gray-600 mt-2 font-semibold">Targets</p>
            </div>
          </div>

          {/* Column 3: Targets Container */}
          <div className={`flex-1 flex justify-center transition-all duration-700 ${stage >= 4 ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-10'}`}>
            <div className="bg-white/50 rounded-2xl p-6 border-2 border-gray-300">
              <h3 className="text-2xl font-bold text-gray-800 mb-4">Target Systems</h3>
              
              <div className="flex flex-col gap-4">
                {/* Mac Browser */}
                <div className="bg-white rounded-xl p-4 shadow-lg border-2 border-orange-200">
                  <div className="flex items-center gap-2 mb-2">
                    <Chrome className="w-5 h-5 text-orange-500" />
                    <h5 className="text-lg font-bold text-gray-800">Mac Browser</h5>
                  </div>
                  <p className="text-sm text-gray-600">iCloud.com automation</p>
                  <p className="text-sm text-gray-500 mt-1">Session persistence</p>
                </div>

                {/* Galaxy Fold */}
                <div className="bg-white rounded-xl p-4 shadow-lg border-2 border-green-200">
                  <div className="flex items-center gap-2 mb-2">
                    <Smartphone className="w-5 h-5 text-green-500" />
                    <h5 className="text-lg font-bold text-gray-800">Galaxy Z Fold 7</h5>
                  </div>
                  <p className="text-sm text-gray-600">Android app control</p>
                  <p className="text-sm text-gray-500 mt-1">ADB enabled</p>
                </div>

                {/* Migration DB */}
                <div className="bg-white rounded-xl p-4 shadow-lg border-2 border-blue-200">
                  <div className="flex items-center gap-2 mb-2">
                    <HardDrive className="w-5 h-5 text-blue-500" />
                    <h5 className="text-lg font-bold text-gray-800">Migration DB</h5>
                  </div>
                  <p className="text-sm text-gray-600">~/.ios_android_migration</p>
                  <p className="text-sm text-gray-500 mt-1">8 tables, 4 views</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 7-Day Migration Journey with Key Innovation Header */}
      <div className={`transition-all duration-700 ${stage >= 5 ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}>
        <div className="max-w-[1200px] mx-auto">
          <div className="bg-white rounded-2xl shadow-xl border-2 border-purple-200 p-6">
            {/* Key Innovation Header */}
            <div className="text-center mb-4">
              <h3 className="text-2xl font-bold text-purple-800 mb-2">Key Innovation</h3>
              <p className="text-lg text-gray-700 mb-3">
                The agent orchestrates complex multi-device, multi-day migration with memory, emotional intelligence, and family coordination.
              </p>
              <div className="flex justify-center gap-8 mb-4">
                <div className="flex items-center gap-2">
                  <Check className="w-6 h-6 text-green-600" />
                  <span className="text-base text-gray-700">Natural conversations</span>
                </div>
                <div className="flex items-center gap-2">
                  <Check className="w-6 h-6 text-green-600" />
                  <span className="text-base text-gray-700">Persistent state</span>
                </div>
                <div className="flex items-center gap-2">
                  <Check className="w-6 h-6 text-green-600" />
                  <span className="text-base text-gray-700">Family respect</span>
                </div>
              </div>
            </div>
              
            <div className="grid grid-cols-4 gap-4">
              {/* iCloud to Google Photos */}
              <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-3 border border-blue-200">
                <div className="flex items-center gap-2 mb-2">
                  <Camera className="w-6 h-6 text-blue-600" />
                  <h4 className="text-base font-bold text-blue-800">0.5TB iCloud Media</h4>
                </div>
                <div className="flex items-center gap-2">
                  <ArrowRight className="w-4 h-4 text-gray-400" />
                  <Cloud className="w-5 h-5 text-green-600" />
                  <p className="text-sm text-gray-700">Google Photos</p>
                </div>
              </div>

              {/* Apple iMessage to WhatsApp */}
              <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-3 border border-green-200">
                <div className="flex items-center gap-2 mb-2">
                  <MessageCircle className="w-6 h-6 text-green-600" />
                  <h4 className="text-base font-bold text-green-800">Apple iMessage</h4>
                </div>
                <div className="flex items-center gap-2">
                  <ArrowRight className="w-4 h-4 text-gray-400" />
                  <Users className="w-5 h-5 text-green-600" />
                  <p className="text-sm text-gray-700">WhatsApp Group</p>
                </div>
              </div>

              {/* Apple Find My to Google Maps */}
              <div className="bg-gradient-to-br from-orange-50 to-amber-50 rounded-xl p-3 border border-orange-200">
                <div className="flex items-center gap-2 mb-2">
                  <MapPin className="w-6 h-6 text-orange-600" />
                  <h4 className="text-base font-bold text-orange-800">Apple Find My</h4>
                </div>
                <div className="flex items-center gap-2">
                  <ArrowRight className="w-4 h-4 text-gray-400" />
                  <MapPin className="w-5 h-5 text-green-600" />
                  <p className="text-sm text-gray-700">Google Maps</p>
                </div>
              </div>

              {/* Apple Cash to Venmo */}
              <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-3 border border-purple-200">
                <div className="flex items-center gap-2 mb-2">
                  <CreditCard className="w-6 h-6 text-purple-600" />
                  <h4 className="text-base font-bold text-purple-800">Apple Cash Teens</h4>
                </div>
                <div className="flex items-center gap-2">
                  <ArrowRight className="w-4 h-4 text-gray-400" />
                  <CreditCard className="w-5 h-5 text-green-600" />
                  <p className="text-sm text-gray-700">Venmo Cards</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default iOS2AndroidArchitectureViz;
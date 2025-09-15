import React, { useState, useEffect } from 'react';
import { Lock, Smartphone, Cloud, MessageCircle, MapPin, CreditCard, Camera, Users, Clock, AlertTriangle, X, Home, School, DollarSign, Image, Video, Wifi, Shield } from 'lucide-react';

const MigrationChallengeViz = () => {
  const [stage, setStage] = useState(0);
  const maxStages = 6;

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
        <h1 className="text-6xl font-bold mb-4">
          <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-red-600 bg-clip-text text-transparent">
            The iOS to Android Migration Challenge
          </span>
        </h1>
        <p className="text-2xl text-gray-700 max-w-5xl mx-auto">
          After 18 years on iPhone, switching isn't just changing phones—it's untangling a digital life
        </p>
      </div>

      {/* Stage 1: The Digital Life Woven Into Apple */}
      <div className={`max-w-[1400px] mx-auto mb-12 transition-all duration-700 ${stage >= 1 ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}>
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-gray-800 mb-2">18 Years of Memories Trapped</h2>
          <p className="text-2xl text-gray-600">Wedding photos, birth videos, religious milestones, family holidays</p>
        </div>
        
        <div className="flex justify-center gap-8">
          {/* Photos Card */}
          <div className="bg-white rounded-2xl p-8 shadow-xl border-2 border-blue-300">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center">
                <Camera className="w-10 h-10 text-white" />
              </div>
              <div>
                <h3 className="text-4xl font-bold text-gray-800">60,238</h3>
                <p className="text-blue-600">Photos</p>
              </div>
            </div>
            <div className="space-y-2 text-gray-600">
              <p className="flex items-center gap-2"><Image className="w-4 h-4 text-blue-500" /> First steps</p>
              <p className="flex items-center gap-2"><Image className="w-4 h-4 text-blue-500" /> Graduations</p>
              <p className="flex items-center gap-2"><Image className="w-4 h-4 text-blue-500" /> Family trips</p>
            </div>
          </div>

          {/* Videos Card */}
          <div className="bg-white rounded-2xl p-8 shadow-xl border-2 border-purple-300">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center">
                <Video className="w-10 h-10 text-white" />
              </div>
              <div>
                <h3 className="text-4xl font-bold text-gray-800">2,418</h3>
                <p className="text-purple-600">Videos</p>
              </div>
            </div>
            <div className="space-y-2 text-gray-600">
              <p className="flex items-center gap-2"><Video className="w-4 h-4 text-purple-500" /> Birth videos</p>
              <p className="flex items-center gap-2"><Video className="w-4 h-4 text-purple-500" /> Birthdays</p>
              <p className="flex items-center gap-2"><Video className="w-4 h-4 text-purple-500" /> Holidays</p>
            </div>
          </div>

          {/* Storage Card */}
          <div className="bg-white rounded-2xl p-8 shadow-xl border-2 border-red-300">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-16 h-16 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center">
                <Cloud className="w-10 h-10 text-white" />
              </div>
              <div>
                <h3 className="text-4xl font-bold text-gray-800">383 GB</h3>
                <p className="text-red-600">in iCloud</p>
              </div>
            </div>
            <div className="space-y-2 text-gray-600">
              <p className="flex items-center gap-2"><Lock className="w-4 h-4 text-red-500" /> Locked in</p>
              <p className="flex items-center gap-2"><Lock className="w-4 h-4 text-red-500" /> No easy export</p>
              <p className="flex items-center gap-2"><Lock className="w-4 h-4 text-red-500" /> 5-7 day process</p>
            </div>
          </div>
        </div>
      </div>

      {/* Stage 2: The Invisible Chains Title */}
      <div className={`max-w-[1400px] mx-auto mb-12 transition-all duration-700 ${stage >= 2 ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}>
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-800 mb-2">The Invisible Chains</h2>
          <p className="text-2xl text-gray-600">Family dependencies that create overwhelming inertia</p>
        </div>
      </div>

      {/* Stage 3-6: Individual Chains */}
      <div className={`max-w-5xl mx-auto grid grid-cols-2 gap-6 transition-all duration-700 ${stage >= 3 ? 'opacity-100' : 'opacity-0'}`}>
        
        {/* Stage 3: iMessage Groups */}
        <div className={`transition-all duration-700 ${stage >= 3 ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-10'}`}>
          <div className="bg-gradient-to-br from-green-100 to-emerald-100 rounded-2xl p-6 shadow-lg border-2 border-green-300">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center">
                <MessageCircle className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800">Family iMessage Group</h3>
            </div>
            <p className="text-xl text-gray-700 mb-3">Where we share our days and coordinate plans</p>
            <div className="bg-white/70 rounded-lg p-3 space-y-2">
              <p className="text-lg text-gray-700 flex items-center gap-2">
                <Users className="w-5 h-5 text-green-600" /> Wife + 3 kids all on iPhone
              </p>
              <p className="text-lg text-gray-700 flex items-center gap-2">
                <X className="w-5 h-5 text-red-500" /> Blue bubbles won't reach Android
              </p>
            </div>
          </div>
        </div>

        {/* Stage 4: Find My */}
        <div className={`transition-all duration-700 ${stage >= 4 ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-10'}`}>
          <div className="bg-gradient-to-br from-orange-100 to-amber-100 rounded-2xl p-6 shadow-lg border-2 border-orange-300">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-orange-500 rounded-full flex items-center justify-center">
                <MapPin className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800">Find My Location</h3>
            </div>
            <p className="text-xl text-gray-700 mb-3">Showing oldest made it to school safely</p>
            <div className="bg-white/70 rounded-lg p-3 space-y-2">
              <p className="text-lg text-gray-700 flex items-center gap-2">
                <School className="w-5 h-5 text-orange-600" /> Track kids to/from school
              </p>
              <p className="text-lg text-gray-700 flex items-center gap-2">
                <Home className="w-5 h-5 text-orange-600" /> Kids track parents too
              </p>
            </div>
          </div>
        </div>

        {/* Stage 5: Apple Cash */}
        <div className={`transition-all duration-700 ${stage >= 5 ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-10'}`}>
          <div className="bg-gradient-to-br from-purple-100 to-pink-100 rounded-2xl p-6 shadow-lg border-2 border-purple-300">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-purple-500 rounded-full flex items-center justify-center">
                <CreditCard className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800">Apple Cash Allowances</h3>
            </div>
            <p className="text-xl text-gray-700 mb-3">Three kids depend on weekly transfers</p>
            <div className="bg-white/70 rounded-lg p-3 space-y-2">
              <p className="text-lg text-gray-700 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-purple-600" /> Teen cards they rely on
              </p>
              <p className="text-lg text-gray-700 flex items-center gap-2">
                <Wifi className="w-5 h-5 text-purple-600" /> Instant family transfers
              </p>
            </div>
          </div>
        </div>

        {/* Stage 6: Family Controls */}
        <div className={`transition-all duration-700 ${stage >= 6 ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-10'}`}>
          <div className="bg-gradient-to-br from-blue-100 to-cyan-100 rounded-2xl p-6 shadow-lg border-2 border-blue-300">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800">Family Controls</h3>
            </div>
            <p className="text-xl text-gray-700 mb-3">Shared albums with grandparents</p>
            <div className="bg-white/70 rounded-lg p-3 space-y-2">
              <p className="text-lg text-gray-700 flex items-center gap-2">
                <Image className="w-5 h-5 text-blue-600" /> Photo streams to family
              </p>
              <p className="text-lg text-gray-700 flex items-center gap-2">
                <Clock className="w-5 h-5 text-blue-600" /> Screen Time controls
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MigrationChallengeViz;
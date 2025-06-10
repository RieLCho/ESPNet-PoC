import React from 'react';
import { Volume2, User, Clock, TrendingUp } from 'lucide-react';

interface Speaker {
  id: string;
  name: string;
  isActive: boolean;
  confidence: number;
  lastSeen: Date;
}

interface SpeakerPanelProps {
  speakers: Speaker[];
}

const SpeakerPanel: React.FC<SpeakerPanelProps> = ({ speakers }) => {
  const formatTimeAgo = (date: Date) => {
    const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
    
    if (seconds < 60) return `${seconds}초 전`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}분 전`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}시간 전`;
    return `${Math.floor(seconds / 86400)}일 전`;
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400';
    if (confidence >= 0.6) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getConfidenceLevel = (confidence: number) => {
    if (confidence >= 0.8) return '높음';
    if (confidence >= 0.6) return '보통';
    return '낮음';
  };

  return (
    <div className="p-6">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <User className="w-5 h-5 mr-2" />
        참여 화자 ({speakers.length})
      </h3>
      
      {speakers.length === 0 ? (
        <div className="text-center text-white/50 py-8">
          <User className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm">등록된 화자가 없습니다</p>
          <p className="text-xs mt-1">음성을 녹음하여 화자를 식별해보세요</p>
        </div>
      ) : (
        <div className="space-y-3">
          {speakers.map((speaker) => (
            <div
              key={speaker.id}
              className={`p-4 rounded-xl border transition-all duration-300 ${
                speaker.isActive
                  ? 'bg-green-500/20 border-green-400/50 shadow-lg shadow-green-400/20'
                  : 'bg-white/5 border-white/10 hover:bg-white/10'
              }`}
            >
              {/* 화자 헤더 */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${
                    speaker.isActive ? 'bg-green-400 animate-pulse' : 'bg-gray-400'
                  }`} />
                  <h4 className="font-medium text-sm">{speaker.name}</h4>
                </div>
                
                {speaker.isActive && (
                  <Volume2 className="w-4 h-4 text-green-400 animate-bounce" />
                )}
              </div>

              {/* 화자 정보 */}
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-white/60 flex items-center">
                    <TrendingUp className="w-3 h-3 mr-1" />
                    신뢰도
                  </span>
                  <span className={`font-medium ${getConfidenceColor(speaker.confidence)}`}>
                    {(speaker.confidence * 100).toFixed(1)}% ({getConfidenceLevel(speaker.confidence)})
                  </span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-white/60 flex items-center">
                    <Clock className="w-3 h-3 mr-1" />
                    마지막 발언
                  </span>
                  <span className="text-white/80">
                    {formatTimeAgo(speaker.lastSeen)}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-white/60">ID</span>
                  <span className="text-white/80 font-mono text-xs">
                    {speaker.id.length > 10 ? `${speaker.id.substring(0, 10)}...` : speaker.id}
                  </span>
                </div>
              </div>

              {/* 신뢰도 바 */}
              <div className="mt-3">
                <div className="w-full bg-white/10 rounded-full h-1.5">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      speaker.confidence >= 0.8 ? 'bg-green-400' :
                      speaker.confidence >= 0.6 ? 'bg-yellow-400' : 'bg-red-400'
                    }`}
                    style={{ width: `${speaker.confidence * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 통계 요약 */}
      {speakers.length > 0 && (
        <div className="mt-6 p-4 bg-white/5 rounded-xl border border-white/10">
          <h4 className="text-sm font-medium mb-3 text-white/80">통계</h4>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-white/60">평균 신뢰도</span>
              <span className="text-white/80">
                {speakers.length > 0 
                  ? `${((speakers.reduce((sum, s) => sum + s.confidence, 0) / speakers.length) * 100).toFixed(1)}%`
                  : '0%'
                }
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/60">활성 화자</span>
              <span className="text-white/80">
                {speakers.filter(s => s.isActive).length} / {speakers.length}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/60">최고 신뢰도</span>
              <span className="text-white/80">
                {speakers.length > 0 
                  ? `${(Math.max(...speakers.map(s => s.confidence)) * 100).toFixed(1)}%`
                  : '0%'
                }
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SpeakerPanel;

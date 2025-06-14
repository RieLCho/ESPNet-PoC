import  { useState, useEffect } from 'react';
import {  Users,  Settings, Wifi, WifiOff } from 'lucide-react';
import VoiceRecorder from './components/VoiceRecorder';
import MetaverseRoom from './components/MetaverseRoom';
import SpeakerPanel from './components/SpeakerPanel';
import SpeechBubble, { type SpeechMessage } from './components/SpeechBubble';

interface Speaker {
  id: string;
  name: string;
  isActive: boolean;
  confidence: number;
  lastSeen: Date;
}

function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [speakers, setSpeakers] = useState<Speaker[]>([]);
  const [currentSpeaker, setCurrentSpeaker] = useState<Speaker | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [serverStatus, setServerStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const [speechMessages, setSpeechMessages] = useState<SpeechMessage[]>([]);

  // 서버 연결 상태 확인
  useEffect(() => {
    const checkServerHealth = async () => {
      try {
        console.log('🔍 서버 상태 확인 중...');
        // localhost 대신 127.0.0.1을 사용해서 테스트
        const response = await fetch('http://127.0.0.1:8000/health', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          mode: 'cors'
        });
        console.log('📡 서버 응답 상태:', response.status);
        if (response.ok) {
          const data = await response.json();
          console.log('✅ 서버 연결 성공:', data);
          console.log('🔄 상태 업데이트: connected');
          setServerStatus('connected');
          setIsConnected(true);
        } else {
          console.log('❌ 서버 응답 실패:', response.status, response.statusText);
          setServerStatus('disconnected');
          setIsConnected(false);
        }
      } catch (error) {
        console.error('💥 서버 연결 오류:', error);
        setServerStatus('disconnected');
        setIsConnected(false);
      }
    };

    checkServerHealth();
    const interval = setInterval(checkServerHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleTextRecognized = (text: string, speakerId: string | null) => {
    const newMessage: SpeechMessage = {
      id: `${Date.now()}-${Math.random()}`,
      text: text,
      speakerId: speakerId,
      timestamp: new Date(),
      isKnown: speakerId !== null
    };
    
    setSpeechMessages(prev => [...prev, newMessage]);
  };

  const handleSpeakerIdentified = (speakerData: any) => {
    if (speakerData.isKnownSpeaker) {
      const newSpeaker: Speaker = {
        id: speakerData.anonymousId,
        name: `Speaker ${speakerData.anonymousId}`,
        isActive: true,
        confidence: speakerData.confidence,
        lastSeen: new Date()
      };

      setCurrentSpeaker(newSpeaker);
      
      // 화자 목록 업데이트
      setSpeakers(prev => {
        const existing = prev.find(s => s.id === newSpeaker.id);
        if (existing) {
          return prev.map(s => 
            s.id === newSpeaker.id 
              ? { ...s, isActive: true, confidence: newSpeaker.confidence, lastSeen: new Date() }
              : { ...s, isActive: false }
          );
        } else {
          return [...prev, newSpeaker];
        }
      });

      // 3초 후 비활성화
      setTimeout(() => {
        setCurrentSpeaker(null);
        setSpeakers(prev => prev.map(s => ({ ...s, isActive: false })));
      }, 3000);
    }
  };

  return (
    <div className="min-h-screen text-white relative overflow-hidden">
      {/* 배경 그라디언트 */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600 via-purple-600 to-pink-600"></div>
      
      {/* 메인 컨테이너 */}
      <div className="relative z-10 flex flex-col h-screen">
        {/* 헤더 */}
        <header className="flex justify-between items-center p-6 bg-white/10 backdrop-blur-sm border-b border-white/20">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">
              🎤 메타버스 화자 인식
            </h1>
            
          </div>
          <div className="flex items-center space-x-2">
              {isConnected ? (
                <>
                  <Wifi className="w-5 h-5 text-green-400" />
                  <span className="text-sm text-green-400">서버 연결됨</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-5 h-5 text-red-400" />
                  <span className="text-sm text-red-400">서버 연결 끊김</span>
                </>
              )}
            </div>
        </header>

        {/* 메인 컨텐츠 */}
        <div className="flex-1 flex">
          {/* 메타버스 룸 (메인 영역) */}
          <div className="flex-1 relative flex flex-col">
            <div className="flex-1">
              <MetaverseRoom 
                speakers={speakers}
                currentSpeaker={currentSpeaker}
              />
            </div>
            
            {/* 말풍선 영역 */}
            <div className="z-10 flex flex-col bg-black/20 backdrop-blur-sm border-t border-white/20" style={{ height: '500px' }}>
              <div className="p-4 flex-shrink-0">
                <h3 className="text-lg font-semibold mb-4 text-center">💬 실시간 음성 인식</h3>
              </div>
              <div className="flex-1 px-4 pb-4 min-h-0">
                <SpeechBubble messages={speechMessages} maxMessages={8} />
              </div>
            </div>
            
            {/* 현재 화자 표시 */}
            {currentSpeaker && (
              <div className="absolute top-6 left-6 bg-black/50 backdrop-blur-sm rounded-2xl p-4 border border-white/20">
                <div className="flex items-center space-x-3">
                  <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                  <div>
                    <h3 className="font-semibold">{currentSpeaker.name}</h3>
                    <p className="text-sm text-white/70">
                      신뢰도: {(currentSpeaker.confidence * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 사이드 패널 */}
          <div className="w-100 bg-black/20 backdrop-blur-sm border-l border-white/20 flex flex-col">
            {/* 음성 녹음 컨트롤 */}
            <div className="p-6 border-b border-white/20">
              <VoiceRecorder
                isRecording={isRecording}
                onRecordingChange={setIsRecording}
                onSpeakerIdentified={handleSpeakerIdentified}
                onTextRecognized={handleTextRecognized}
                isConnected={isConnected}
              />
            </div>

            {/* 화자 목록 */}
            <div className="flex-1">
              <SpeakerPanel speakers={speakers} />
            </div>

            {/* 통계 */}
            <div className="p-6 border-t border-white/20">
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-white/70">서버 상태</span>
                  <span className={`font-medium ${
                    serverStatus === 'connected' ? 'text-green-400' : 
                    serverStatus === 'connecting' ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {serverStatus === 'connected' ? '정상' : 
                     serverStatus === 'connecting' ? '연결 중' : '연결 끊김'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-white/70">등록된 화자</span>
                  <span className="font-medium">{speakers.length}명</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-white/70">활성 화자</span>
                  <span className="font-medium">
                    {speakers.filter(s => s.isActive).length}명
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 푸터 */}
        <footer className="p-4 bg-black/20 backdrop-blur-sm border-t border-white/20 text-center">
          <p className="text-sm text-white/70">
            ESPNet 기반 실시간 화자 인식 시스템
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;

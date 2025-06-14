import React, { useEffect, useState, useRef } from 'react';
import { User, UserCheck } from 'lucide-react';

interface SpeechMessage {
  id: string;
  text: string;
  speakerId: string | null;
  timestamp: Date;
  isKnown: boolean;
}

interface SpeechBubbleProps {
  messages: SpeechMessage[];
  maxMessages?: number;
}

const SpeechBubble: React.FC<SpeechBubbleProps> = ({ messages, maxMessages = 10 }) => {
  const [visibleMessages, setVisibleMessages] = useState<SpeechMessage[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 최신 메시지들만 표시 (최대 개수 제한)
    const recentMessages = messages.slice(-maxMessages);
    setVisibleMessages(recentMessages);
  }, [messages, maxMessages]);

  // 새 메시지가 추가될 때 자동 스크롤
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [visibleMessages]);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('ko-KR', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  const getSpeakerColor = (speakerId: string | null, isKnown: boolean) => {
    if (!speakerId || !isKnown) {
      return 'bg-gray-500'; // 알 수 없는 화자
    }
    
    // 화자 ID를 기반으로 색상 결정 (간단한 해시)
    const colors = [
      'bg-blue-500',
      'bg-green-500', 
      'bg-purple-500',
      'bg-pink-500',
      'bg-yellow-500',
      'bg-indigo-500',
      'bg-red-500',
      'bg-teal-500'
    ];
    
    const hash = speakerId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
  };

  const getSpeakerPosition = (index: number) => {
    // 메시지를 번갈아가며 왼쪽, 오른쪽에 배치
    return index % 2 === 0 ? 'left' : 'right';
  };

  if (visibleMessages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-white/70 bg-gray-800/50 rounded-lg">
        <div className="text-center p-8">
          <div className="text-4xl mb-2">🎙️</div>
          <p className="text-white">음성을 입력하면 여기에 말풍선이 나타납니다</p>
          <p className="text-xs mt-2 text-white/50">10초간 말하면 자동으로 인식됩니다</p>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={scrollRef}
      className="h-full overflow-y-auto space-y-4 scroll-smooth bg-gray-800/30 rounded-lg p-4 speech-bubble-scroll"
      style={{ scrollBehavior: 'smooth' }}
    >
      {visibleMessages.map((message, index) => {
        const position = getSpeakerPosition(index);
        const speakerColor = getSpeakerColor(message.speakerId, message.isKnown);
        
        return (
          <div
            key={message.id}
            className={`flex items-start gap-3 ${
              position === 'right' ? 'flex-row-reverse' : 'flex-row'
            }`}
          >
            {/* 화자 아바타 */}
            <div className={`flex-shrink-0 w-10 h-10 rounded-full ${speakerColor} flex items-center justify-center text-white shadow-lg transition-all duration-300 hover:scale-110`}>
              {message.isKnown ? (
                <UserCheck className="w-5 h-5" />
              ) : (
                <User className="w-5 h-5" />
              )}
            </div>
            
            {/* 말풍선 */}
            <div 
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-2xl text-sm shadow-lg transition-all duration-300 hover:shadow-xl ${
                position === 'right'
                  ? 'bg-blue-500 text-white rounded-br-none'
                  : 'bg-white/10 text-white rounded-bl-none backdrop-blur-sm border border-white/20'
              }`}
            >
              {/* 화자 정보 */}
              <div className={`text-xs mb-1 ${
                position === 'right' ? 'text-blue-100' : 'text-white/70'
              }`}>
                {message.speakerId || '알 수 없는 화자'} • {formatTime(message.timestamp)}
              </div>
              
              {/* 메시지 텍스트 */}
              <div className="break-words">
                {message.text}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default SpeechBubble;
export type { SpeechMessage };

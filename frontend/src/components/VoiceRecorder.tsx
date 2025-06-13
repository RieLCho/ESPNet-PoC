import React, { useState, useRef, useCallback } from 'react';
import { Mic, MicOff } from 'lucide-react';

interface VoiceRecorderProps {
  isRecording: boolean;
  onRecordingChange: (recording: boolean) => void;
  onSpeakerIdentified: (speakerData: any) => void;
  onTextRecognized: (text: string, speakerId: string | null) => void;
  isConnected: boolean;
}

const VoiceRecorder: React.FC<VoiceRecorderProps> = ({
  isRecording,
  onRecordingChange,
  onSpeakerIdentified,
  onTextRecognized,
  isConnected
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [registrationMode, setRegistrationMode] = useState(false);
  const [speakerId, setSpeakerId] = useState('');
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);

  const startRecording = useCallback(async () => {
    try {
      console.log('🎙️ 녹음 시작 시도:', { isConnected, registrationMode, speakerId });
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        } 
      });
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      });
      
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await processAudio(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      onRecordingChange(true);
      
      // 타이머 시작
      setRecordingTime(0);
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
      // 10초 후 자동 중지
      setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          stopRecording();
        }
      }, 10000);
      
    } catch (err) {
      setError('마이크 접근이 거부되었습니다.');
      console.error('Error accessing microphone:', err);
    }
  }, [onRecordingChange]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      onRecordingChange(false);
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  }, [onRecordingChange]);

  const processAudio = async (audioBlob: Blob) => {
    console.log('🔊 오디오 처리 시작:', { isConnected, size: audioBlob.size });
    
    // 실시간으로 서버 연결 상태 재확인
    let serverConnected = isConnected;
    if (!serverConnected) {
      console.log('🔄 서버 연결 상태 재확인...');
      try {
        const healthResponse = await fetch('http://127.0.0.1:8000/health', {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          mode: 'cors'
        });
        serverConnected = healthResponse.ok;
        console.log('🔄 재확인 결과:', serverConnected);
      } catch (error) {
        console.error('🔄 재확인 실패:', error);
        serverConnected = false;
      }
    }
    
    if (!serverConnected) {
      console.error('❌ 서버 연결 상태:', serverConnected);
      setError('서버에 연결되어 있지 않습니다.');
      return;
    }

    setIsProcessing(true);
    console.log('오디오 처리 시작:', { size: audioBlob.size, type: audioBlob.type });
    
    try {
      // Blob을 base64로 변환
      const reader = new FileReader();
      reader.onloadend = async () => {
        try {
          const base64Audio = (reader.result as string).split(',')[1];
          console.log('Base64 변환 완료, 길이:', base64Audio.length);
          
          const endpoint = registrationMode ? '/speakers/register' : '/speakers/identify';
          const payload = registrationMode 
            ? {
                anonymousId: speakerId || `speaker_${Date.now()}`,
                audioData: base64Audio,
                metadata: { registeredAt: new Date().toISOString() }
              }
            : {
                audioData: base64Audio,
                threshold: 0.7
              };

          console.log('API 요청 시작:', { endpoint, payloadSize: JSON.stringify(payload).length });

          const response = await fetch(`http://127.0.0.1:8000${endpoint}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-API-Key': 'metaverse_demo_key'
            },
            body: JSON.stringify(payload)
          });

          console.log('서버 응답:', { status: response.status, statusText: response.statusText });

          if (!response.ok) {
            const errorText = await response.text();
            console.error('서버 오류 응답:', errorText);
            throw new Error(`서버 오류: ${response.status} - ${errorText}`);
          }

          const result = await response.json();
          console.log('응답 데이터:', result);
          
          if (registrationMode) {
            setError(null);
            setSpeakerId('');
            setRegistrationMode(false);
            setError(`등록 완료: ${result.anonymousId || '알 수 없음'}`);
          } else {
            onSpeakerIdentified(result);
            // 인식된 텍스트가 있으면 콜백 호출
            console.log('🔍 텍스트 인식 체크:', { 
              hasRecognizedText: !!result.recognizedText, 
              recognizedText: result.recognizedText,
              anonymousId: result.anonymousId 
            });
            if (result.recognizedText) {
              console.log('✅ onTextRecognized 호출:', result.recognizedText, result.anonymousId);
              onTextRecognized(result.recognizedText, result.anonymousId);
            } else {
              console.log('❌ recognizedText가 없음 또는 falsy');
            }
          }
        } catch (fetchError) {
          console.error('Fetch 오류:', fetchError);
          setError(`네트워크 오류: ${(fetchError as Error).message}`);
        }
      };
      
      reader.onerror = () => {
        console.error('FileReader 오류');
        setError('오디오 파일 읽기 실패');
      };
      
      reader.readAsDataURL(audioBlob);
    } catch (err) {
      setError(`오류가 발생했습니다: ${(err as Error).message}`);
      console.error('Error processing audio:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const formatTime = (seconds: number) => {
    return `${Math.floor(seconds / 60)}:${(seconds % 60).toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h3 className="text-lg font-semibold mb-2">음성 인식</h3>
        
        {/* 모드 선택 */}
        <div className="flex space-x-2 mb-4">
          <button
            onClick={() => setRegistrationMode(false)}
            className={`px-3 py-1 rounded-lg text-sm transition-colors ${
              !registrationMode 
                ? 'bg-blue-500 text-white' 
                : 'bg-white/10 text-white/70 hover:bg-white/20'
            }`}
          >
            식별 모드
          </button>
          <button
            onClick={() => setRegistrationMode(true)}
            className={`px-3 py-1 rounded-lg text-sm transition-colors ${
              registrationMode 
                ? 'bg-green-500 text-white' 
                : 'bg-white/10 text-white/70 hover:bg-white/20'
            }`}
          >
            등록 모드
          </button>
        </div>

        {/* 화자 ID 입력 (등록 모드일 때만) */}
        {registrationMode && (
          <div className="mb-4">
            <input
              type="text"
              placeholder="화자 ID 입력 (예: user123)"
              value={speakerId}
              onChange={(e) => setSpeakerId(e.target.value)}
              className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
        )}
        
        {/* 녹음 버튼 */}
        <button
          onClick={() => {
            console.log('🔘 버튼 클릭:', { 
              isRecording, 
              isProcessing, 
              isConnected, 
              registrationMode, 
              speakerId: speakerId.trim(),
              disabled: isProcessing || !isConnected || (registrationMode && !speakerId.trim())
            });
            if (isRecording) {
              stopRecording();
            } else {
              startRecording();
            }
          }}
          disabled={isProcessing || !isConnected || (registrationMode && !speakerId.trim())}
          className={`w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 ${
            isRecording
              ? 'bg-red-500 hover:bg-red-600 animate-pulse'
              : isConnected
              ? 'bg-blue-500 hover:bg-blue-600'
              : 'bg-gray-500 cursor-not-allowed'
          } ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {isProcessing ? (
            <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : isRecording ? (
            <MicOff className="w-8 h-8 text-white" />
          ) : (
            <Mic className="w-8 h-8 text-white" />
          )}
        </button>
        
        {/* 상태 표시 */}
        <div className="mt-4 text-sm">
          {isRecording && (
            <div className="text-red-400 animate-pulse">
              🔴 녹음 중... {formatTime(recordingTime)}
            </div>
          )}
          {isProcessing && (
            <div className="text-yellow-400">
              ⏳ 처리 중...
            </div>
          )}
          {!isConnected && (
            <div className="text-red-400">
              ❌ 서버 연결 끊김
            </div>
          )}
        </div>
        
        {/* 오류 메시지 */}
        {error && (
          <div className="mt-2 p-2 bg-red-500/20 border border-red-500/50 rounded-lg text-red-200 text-sm">
            {error}
          </div>
        )}
        
        {/* 도움말 */}
        <div className="mt-4 text-xs text-white/50">
          {registrationMode 
            ? '새로운 화자를 등록하려면 화자 ID를 입력하고 10초간 말하세요.'
            : '10초간 말하면 자동으로 화자를 식별합니다.'
          }
        </div>
      </div>
    </div>
  );
};

export default VoiceRecorder;

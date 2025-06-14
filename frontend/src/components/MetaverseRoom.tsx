import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';

interface Speaker {
  id: string;
  name: string;
  isActive: boolean;
  confidence: number;
  lastSeen: Date;
}

interface MetaverseRoomProps {
  speakers: Speaker[];
  currentSpeaker: Speaker | null;
}

const MetaverseRoom: React.FC<MetaverseRoomProps> = ({ speakers, currentSpeaker }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const avatarsRef = useRef<Map<string, THREE.Mesh>>(new Map());

  useEffect(() => {
    if (!mountRef.current) return;

    // Scene 설정
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000011);
    sceneRef.current = scene;

    // Camera 설정
    const camera = new THREE.PerspectiveCamera(
      75,
      mountRef.current.clientWidth / mountRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.set(0, 5, 10);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // Renderer 설정
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    renderer.setClearColor(0x000000, 0);
    renderer.domElement.style.position = 'absolute';
    renderer.domElement.style.top = '0';
    renderer.domElement.style.left = '0';
    renderer.domElement.style.zIndex = '1';
    rendererRef.current = renderer;
    mountRef.current.appendChild(renderer.domElement);

    // 조명 설정
    const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(5, 5, 5);
    scene.add(directionalLight);

    // 바닥 생성
    const floorGeometry = new THREE.PlaneGeometry(20, 20);
    const floorMaterial = new THREE.MeshLambertMaterial({ 
      color: 0x333366,
      transparent: true,
      opacity: 0.8
    });
    const floor = new THREE.Mesh(floorGeometry, floorMaterial);
    floor.rotation.x = -Math.PI / 2;
    scene.add(floor);

    // 격자 추가
    const gridHelper = new THREE.GridHelper(20, 20, 0x444477, 0x444477);
    scene.add(gridHelper);

    // 파티클 시스템 (별들)
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesCount = 1000;
    const posArray = new Float32Array(particlesCount * 3);

    for (let i = 0; i < particlesCount * 3; i++) {
      posArray[i] = (Math.random() - 0.5) * 100;
    }

    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const particlesMaterial = new THREE.PointsMaterial({
      size: 0.005,
      color: 0x888899
    });
    const particlesMesh = new THREE.Points(particlesGeometry, particlesMaterial);
    scene.add(particlesMesh);

    // 애니메이션 루프
    const animate = () => {
      requestAnimationFrame(animate);
      
      // 파티클 회전
      particlesMesh.rotation.y += 0.0002;
      
      // 아바타 애니메이션
      avatarsRef.current.forEach((avatar, speakerId) => {
        const speaker = speakers.find(s => s.id === speakerId);
        if (speaker?.isActive) {
          avatar.scale.setScalar(1.2 + Math.sin(Date.now() * 0.01) * 0.1);
        } else {
          avatar.scale.setScalar(1.0);
        }
      });
      
      renderer.render(scene, camera);
    };
    animate();

    // 리사이즈 핸들러
    const handleResize = () => {
      if (!mountRef.current) return;
      
      camera.aspect = mountRef.current.clientWidth / mountRef.current.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    };
    
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // 화자 아바타 업데이트
  useEffect(() => {
    if (!sceneRef.current) return;

    // 기존 아바타들 제거
    avatarsRef.current.forEach((avatar) => {
      sceneRef.current!.remove(avatar);
    });
    avatarsRef.current.clear();

    // 새로운 아바타들 생성
    speakers.forEach((speaker, index) => {
      const avatarGeometry = new THREE.SphereGeometry(0.5, 16, 16);
      const avatarMaterial = new THREE.MeshLambertMaterial({
        color: speaker.isActive ? 0x00ff00 : 0x4466ff,
        emissive: speaker.isActive ? 0x002200 : 0x000022,
        transparent: true,
        opacity: 0.9
      });
      
      const avatar = new THREE.Mesh(avatarGeometry, avatarMaterial);
      
      // 원형으로 배치
      const angle = (index / speakers.length) * Math.PI * 2;
      const radius = 3;
      avatar.position.set(
        Math.cos(angle) * radius,
        1,
        Math.sin(angle) * radius
      );
      
      // 네임태그 추가
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d')!;
      canvas.width = 256;
      canvas.height = 64;
      
      context.fillStyle = 'rgba(0, 0, 0, 0.8)';
      context.fillRect(0, 0, canvas.width, canvas.height);
      
      context.fillStyle = 'white';
      context.font = '24px Arial';
      context.textAlign = 'center';
      context.fillText(speaker.name, canvas.width / 2, 40);
      
      const texture = new THREE.CanvasTexture(canvas);
      const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
      const sprite = new THREE.Sprite(spriteMaterial);
      sprite.position.set(0, 1.5, 0);
      sprite.scale.set(2, 0.5, 1);
      avatar.add(sprite);
      
      sceneRef.current!.add(avatar);
      avatarsRef.current.set(speaker.id, avatar);
    });
  }, [speakers]);

  return (
    <div className="w-full h-full relative">
      <div ref={mountRef} className="w-full h-full relative z-0" />
      
      {/* 2D 오버레이 */}
      <div className="absolute inset-0 pointer-events-none z-10">
        {/* 중앙 로고 */}
        <div className="relative w-80 pt-4">
          <div className="bg-black/30 backdrop-blur-sm rounded-full p-8 border border-white/20">
            <h2 className="text-4xl font-bold text-white text-center mb-2">
              🌌 MetaVerse
            </h2>
            <p className="text-white/70 text-center">화자 인식 공간</p>
          </div>
        </div>
        
        {/* 하단 정보 */}
        <div className="absolute bottom-6 left-6 right-6">
          <div className="flex justify-between items-center">
            <div className="bg-black/50 backdrop-blur-sm rounded-xl p-3 border border-white/20">
              <p className="text-sm text-white/70">
                💬 실시간 화자 식별 중...
              </p>
            </div>
            
            {currentSpeaker && (
              <div className="bg-green-500/20 backdrop-blur-sm rounded-xl p-3 border border-green-400/50">
                <p className="text-sm text-green-200">
                  🗣️ {currentSpeaker.name} 발언 중 ({(currentSpeaker.confidence * 100).toFixed(1)}%)
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetaverseRoom;

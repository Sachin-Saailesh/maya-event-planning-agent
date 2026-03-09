import React, { useRef, useEffect } from 'react';

export default function AudioWaveform({ room }) {
  const canvasRef = useRef(null);
  const animationRef = useRef();

  useEffect(() => {
    if (!room || !room.localParticipant) return;

    let cleanup = null;

    const initVisualizer = () => {
      const pubs = Array.from(room.localParticipant.audioTrackPublications.values());
      const audioTrack = pubs[0]?.audioTrack;
      if (!audioTrack || !audioTrack.mediaStreamTrack) return false;

      const stream = new MediaStream([audioTrack.mediaStreamTrack]);
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      
      analyser.fftSize = 64; 
      source.connect(analyser);

      const canvas = canvasRef.current;
      if (!canvas) return true;
      const ctx = canvas.getContext('2d');
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const draw = () => {
        if (!canvasRef.current) return;
        animationRef.current = requestAnimationFrame(draw);
        
        analyser.getByteFrequencyData(dataArray);
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const activeBins = Math.floor(bufferLength * 0.75); // Use lower frequencies mostly
        const spacing = 2;
        const totalSpacing = spacing * (activeBins - 1);
        const barWidth = Math.max(2, (canvas.width - totalSpacing) / activeBins);
        let x = 0;

        for (let i = 0; i < activeBins; i++) {
          // Normalize 0-255 to a decent height, min 4px
          let rawHeight = (dataArray[i] / 255) * canvas.height * 1.5;
          const barHeight = Math.max(4, Math.min(rawHeight, canvas.height));

          // Maya Gold theme
          ctx.fillStyle = `rgb(218, 165, 32)`; 
          
          const y = (canvas.height - barHeight) / 2;
          
          ctx.beginPath();
          ctx.roundRect(x, y, barWidth, barHeight, 2);
          ctx.fill();

          x += barWidth + spacing;
        }
      };

      draw();

      return () => {
        if (animationRef.current) cancelAnimationFrame(animationRef.current);
        if (audioContext.state !== 'closed') {
          audioContext.close();
        }
      };
    };

    cleanup = initVisualizer();
    
    if (!cleanup) {
      let attempts = 0;
      const interval = setInterval(() => {
        attempts++;
        const success = initVisualizer();
        if (success || attempts > 20) {
          clearInterval(interval);
          if (typeof success === 'function') cleanup = success;
        }
      }, 250);
      return () => {
        clearInterval(interval);
        if (typeof cleanup === 'function') cleanup();
      };
    }

    return () => {
      if (typeof cleanup === 'function') cleanup();
    };

  }, [room]);

  return (
    <div style={{ display: 'flex', alignItems: 'center', marginRight: '16px' }}>
      <canvas 
        ref={canvasRef} 
        width={60} 
        height={24} 
        style={{
          background: 'transparent'
        }} 
      />
    </div>
  );
}

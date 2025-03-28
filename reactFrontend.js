import React, { useState, useEffect, useRef } from 'react';
import { Clock, ScanLine, Camera, X, Check, Delete } from 'lucide-react';

function App() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [employeeId, setEmployeeId] = useState('');
  const videoRef = useRef<HTMLVideoElement>(null);
  const [cameraError, setCameraError] = useState<string>('');

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    const startWebcam = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          video: { 
            width: { ideal: 1280 },
            height: { ideal: 720 }
          }
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        setCameraError('Unable to access camera. Please ensure camera permissions are granted.');
        console.error('Error accessing webcam:', err);
      }
    };

    startWebcam();

    return () => {
      clearInterval(timer);
      if (videoRef.current?.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });
  };

  const handleKeyPress = (value: string) => {
    if (value === 'clear') {
      setEmployeeId('');
    } else if (value === 'backspace') {
      setEmployeeId(prev => prev.slice(0, -1));
    } else if (value === 'submit') {
      // Handle submit logic here
      console.log('Submitted ID:', employeeId);
      setEmployeeId('');
    } else {
      setEmployeeId(prev => prev.length < 10 ? prev + value : prev);
    }
  };

  const KeypadButton = ({ value, color = 'bg-[#4a4a4a] hover:bg-[#5a5a5a]', onClick, fullWidth = false }: { value: string, color?: string, onClick: () => void, fullWidth?: boolean }) => (
    <button
      onClick={onClick}
      className={`${color} ${fullWidth ? 'col-span-3' : ''} active:scale-95 text-white font-bold rounded-lg p-4 text-2xl transition-all duration-150 ease-in-out shadow-lg flex items-center justify-center gap-2 min-h-[4rem] border-2 border-[#3a3a3a]`}
    >
      {value === 'backspace' ? <Delete className="h-6 w-6" /> :
       value === 'clear' ? <X className="h-6 w-6" /> :
       value === 'submit' ? (
         <>
           <Check className="h-6 w-6" />
           <span>SUBMIT</span>
         </>
       ) : value}
    </button>
  );

  return (
    <div className="min-h-screen bg-[#212121] text-white">
      {/* Header */}
      <header className="bg-black bg-opacity-50 p-4">
        <div className="container mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <img 
              src="https://i.imgur.com/vqMWvZ9.png" 
              alt="MSI Strategic Staffing" 
              className="h-12"
            />
            <h1 className="text-2xl font-bold">MSI Strategic Staffing</h1>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Time Display and Keypad */}
          <div className="space-y-8">
            <div className="bg-[#2a2a2a] rounded-lg p-8 shadow-xl">
              <div className="text-center">
                <p className="text-xl mb-4">{formatDate(currentTime)}</p>
                <div className="text-6xl font-bold mb-6 text-[#A4D233]">
                  {formatTime(currentTime)}
                </div>
              </div>
            </div>
            
            {/* Keypad */}
            <div className="bg-[#2a2a2a] rounded-lg p-8 shadow-xl">
              <div className="mb-6">
                <input
                  type="text"
                  value={employeeId}
                  readOnly
                  placeholder="Enter Employee ID"
                  className="w-full bg-[#212121] text-2xl p-4 rounded-lg text-center font-ibm-plex tracking-wider"
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(num => (
                  <KeypadButton
                    key={num}
                    value={num.toString()}
                    color="bg-gradient-to-br from-[#4a4a4a] to-[#5a5a5a] hover:from-[#5a5a5a] hover:to-[#6a6a6a]"
                    onClick={() => handleKeyPress(num.toString())}
                  />
                ))}
                <KeypadButton
                  value="clear"
                  color="bg-gradient-to-br from-red-600 to-red-700 hover:from-red-500 hover:to-red-600"
                  onClick={() => handleKeyPress('clear')}
                />
                <KeypadButton
                  value="0"
                  color="bg-gradient-to-br from-[#4a4a4a] to-[#5a5a5a] hover:from-[#5a5a5a] hover:to-[#6a6a6a]"
                  onClick={() => handleKeyPress('0')}
                />
                <KeypadButton
                  value="backspace"
                  color="bg-gradient-to-br from-yellow-600 to-yellow-700 hover:from-yellow-500 hover:to-yellow-600"
                  onClick={() => handleKeyPress('backspace')}
                />
                <KeypadButton
                  value="submit"
                  color="bg-gradient-to-br from-[#A4D233] to-[#93bd2e] hover:from-[#b3e142] hover:to-[#a2cc3d]"
                  onClick={() => handleKeyPress('submit')}
                  fullWidth
                />
              </div>
            </div>
          </div>

          {/* Webcam Preview and Scan Section */}
          <div className="bg-[#2a2a2a] rounded-lg p-8 shadow-xl">
            <div className="relative mb-6 rounded-lg overflow-hidden bg-black aspect-video">
              {cameraError ? (
                <div className="absolute inset-0 flex items-center justify-center text-center p-4 bg-[#212121]">
                  <div>
                    <Camera className="h-16 w-16 text-red-400 mx-auto mb-4" />
                    <p className="text-red-400">{cameraError}</p>
                  </div>
                </div>
              ) : (
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
              )}
            </div>
            <div className="text-center">
              <ScanLine className="h-16 w-16 text-[#A4D233] mb-4 mx-auto" />
              <h2 className="text-2xl font-bold mb-2">Please scan your ID</h2>
              <p className="text-xl text-gray-400">Por favor pase su tarjeta</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 w-full bg-black bg-opacity-50 p-4">
        <div className="container mx-auto text-center text-gray-400">
          <p>© 2025 MSI Strategic Staffing. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
import React, { useState, useEffect, useRef } from "react";
import { ScanLine, Camera, Loader2 } from "lucide-react";
import KeypadButton from "./components/KeypadButton";
import StatusMessage from "./components/StatusMessage";
import { initializeSoapClient, submitPunch } from "./services/soapService";
import settings from "./settings.json";

// Initialize SOAP client with settings
initializeSoapClient({
  endpoint: settings.soap.endpoint,
  username: settings.soap.username,
  password: settings.soap.password,
  clientId: settings.soap.clientId.toString(),
  timeout: settings.soap.timeout,
});

function App() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [employeeId, setEmployeeId] = useState("");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [statusMessageEs, setStatusMessageEs] = useState<string>("");
  const [statusType, setStatusType] = useState<"success" | "warning" | "error">(
    "success"
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [cameraError, setCameraError] = useState<string>("");
  const videoStreamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    const startWebcam = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoStreamRef.current = stream;
        }
      } catch (err) {
        setCameraError(
          "Unable to access camera. Please ensure camera permissions are granted."
        );
        console.error("Error accessing webcam:", err);
      }
    };

    startWebcam();

    return () => {
      clearInterval(timer);
      if (videoStreamRef.current) {
        videoStreamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  };

  const handleKeyPress = async (value: string) => {
    if (isSubmitting) return;

    if (value === "clear") {
      setEmployeeId("");
      setStatusMessage("");
      setStatusMessageEs("");
    } else if (value === "backspace") {
      setEmployeeId((prev) => prev.slice(0, -1));
    } else if (value === "submit") {
      if (!employeeId) {
        setStatusMessage("Please enter an employee ID");
        setStatusMessageEs("Por favor ingrese su ID de empleado");
        setStatusType("error");
        return;
      }

      setIsSubmitting(true);
      try {
        const response = await submitPunch(employeeId);

        setStatusMessage(response.message);
        setStatusMessageEs(response.messageEs);
        setStatusType(response.success ? "success" : "error");

        if (response.success) {
          setEmployeeId("");

          // Show punch type and weekly hours if available
          if (response.punchType && response.weeklyHours !== undefined) {
            const punchTypeMsg =
              response.punchType === "checkin" ? "Clock In" : "Clock Out";
            const punchTypeMsgEs =
              response.punchType === "checkin" ? "Entrada" : "Salida";
            setStatusMessage(
              `${
                response.message
              } - ${punchTypeMsg} (${response.weeklyHours.toFixed(2)} hrs)`
            );
            setStatusMessageEs(
              `${
                response.messageEs
              } - ${punchTypeMsgEs} (${response.weeklyHours.toFixed(2)} hrs)`
            );
          }
        }
      } catch (error) {
        setStatusMessage("Failed to record punch");
        setStatusMessageEs("Error al registrar");
        setStatusType("error");
        console.error("Punch error:", error);
      } finally {
        setIsSubmitting(false);
      }
    } else {
      setEmployeeId((prev) => (prev.length < 10 ? prev + value : prev));
    }
  };

  return (
    <div className="min-h-screen bg-[#212121] text-white">
      {/* Header */}
      <header className="bg-black/50 p-4 shadow-lg">
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
      <main className="container mx-auto p-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Time Display and Keypad */}
          <div className="space-y-8">
            <div className="bg-[#2a2a2a] rounded-xl p-8 shadow-2xl border border-[#3a3a3a]">
              <div className="text-center">
                <p className="text-2xl mb-4 text-gray-400">
                  {formatDate(currentTime)}
                </p>
                <div className="text-7xl font-bold mb-6 text-[#A4D233] tracking-tight">
                  {formatTime(currentTime)}
                </div>
              </div>
            </div>

            {/* Status Message */}
            {statusMessage && (
              <StatusMessage
                type={statusType}
                message={statusMessage}
                messageEs={statusMessageEs}
              />
            )}

            {/* Keypad */}
            <div className="bg-[#2a2a2a] rounded-xl p-8 shadow-2xl border border-[#3a3a3a]">
              <div className="mb-8">
                <input
                  type="text"
                  value={employeeId}
                  readOnly
                  placeholder="Enter Employee ID"
                  className="w-full bg-[#1a1a1a] text-2xl p-6 rounded-xl text-center font-ibm-plex tracking-wider border-2 border-[#3a3a3a] focus:outline-none"
                />
              </div>
              <div className="grid grid-cols-3 gap-6">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => (
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
                  onClick={() => handleKeyPress("clear")}
                />
                <KeypadButton
                  value="0"
                  color="bg-gradient-to-br from-[#4a4a4a] to-[#5a5a5a] hover:from-[#5a5a5a] hover:to-[#6a6a6a]"
                  onClick={() => handleKeyPress("0")}
                />
                <KeypadButton
                  value="backspace"
                  color="bg-gradient-to-br from-yellow-600 to-yellow-700 hover:from-yellow-500 hover:to-yellow-600"
                  onClick={() => handleKeyPress("backspace")}
                />
                <KeypadButton
                  value={
                    isSubmitting ? (
                      <Loader2 className="h-6 w-6 animate-spin" />
                    ) : (
                      "submit"
                    )
                  }
                  color="bg-gradient-to-br from-[#A4D233] to-[#93bd2e] hover:from-[#b3e142] hover:to-[#a2cc3d]"
                  onClick={() => handleKeyPress("submit")}
                  fullWidth
                />
              </div>
            </div>
          </div>

          {/* Webcam Preview and Scan Section */}
          <div className="bg-[#2a2a2a] rounded-xl p-8 shadow-2xl border border-[#3a3a3a]">
            <div className="relative mb-8 rounded-xl overflow-hidden bg-black aspect-video">
              {cameraError ? (
                <div className="absolute inset-0 flex items-center justify-center text-center p-4 bg-[#1a1a1a]">
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
              <ScanLine className="h-20 w-20 text-[#A4D233] mb-6 mx-auto animate-pulse" />
              <h2 className="text-3xl font-bold mb-3">Please scan your ID</h2>
              <p className="text-xl text-gray-400">Por favor pase su tarjeta</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 w-full bg-black/50 p-4 backdrop-blur-sm">
        <div className="container mx-auto text-center text-gray-400">
          <p>© 2025 MSI Strategic Staffing. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default App;

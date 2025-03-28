import React from "react";
import { AlertCircle, CheckCircle, AlertTriangle } from "lucide-react";

interface StatusMessageProps {
  type: "success" | "warning" | "error";
  message: string;
  messageEs: string;
}

const StatusMessage: React.FC<StatusMessageProps> = ({
  type,
  message,
  messageEs,
}) => {
  const getIcon = () => {
    switch (type) {
      case "success":
        return <CheckCircle className="h-8 w-8 text-green-400" />;
      case "warning":
        return <AlertTriangle className="h-8 w-8 text-yellow-400" />;
      case "error":
        return <AlertCircle className="h-8 w-8 text-red-400" />;
    }
  };

  const getBgColor = () => {
    switch (type) {
      case "success":
        return "bg-green-500/10 border-green-500/20";
      case "warning":
        return "bg-yellow-500/10 border-yellow-500/20";
      case "error":
        return "bg-red-500/10 border-red-500/20";
    }
  };

  const getTextColor = () => {
    switch (type) {
      case "success":
        return "text-green-400";
      case "warning":
        return "text-yellow-400";
      case "error":
        return "text-red-400";
    }
  };

  return (
    <div
      className={`rounded-xl p-6 border ${getBgColor()} backdrop-blur-sm animate-fadeIn`}
    >
      <div className="flex items-start gap-4">
        {getIcon()}
        <div className="space-y-1">
          <p className={`text-lg font-medium ${getTextColor()}`}>{message}</p>
          <p className="text-gray-400">{messageEs}</p>
        </div>
      </div>
    </div>
  );
};

export default StatusMessage;

import React, { ReactNode } from "react";
import { Delete, X, Check } from "lucide-react";

interface KeypadButtonProps {
  value: string | ReactNode;
  color?: string;
  onClick: () => void;
  fullWidth?: boolean;
}

export const KeypadButton: React.FC<KeypadButtonProps> = ({
  value,
  color = "bg-gradient-to-br from-[#4a4a4a] to-[#5a5a5a] hover:from-[#5a5a5a] hover:to-[#6a6a6a]",
  onClick,
  fullWidth = false,
}) => (
  <button
    onClick={onClick}
    className={`${color} ${
      fullWidth ? "col-span-3" : ""
    } active:scale-95 text-white font-bold rounded-xl p-6 text-2xl transition-all duration-150 ease-in-out shadow-xl hover:shadow-2xl flex items-center justify-center gap-3 min-h-[4.5rem] border border-[#3a3a3a]`}
  >
    {typeof value === "string" ? (
      value === "backspace" ? (
        <Delete className="h-7 w-7" />
      ) : value === "clear" ? (
        <X className="h-7 w-7" />
      ) : value === "submit" ? (
        <>
          <Check className="h-7 w-7" />
          <span>SUBMIT</span>
        </>
      ) : (
        value
      )
    ) : (
      value
    )}
  </button>
);

export default KeypadButton;

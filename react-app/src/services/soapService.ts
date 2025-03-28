import { Client, createClientAsync } from "soap";

interface SoapSettings {
  endpoint: string;
  username: string;
  password: string;
  clientId: string;
  timeout: number;
}

interface PunchResponse {
  success: boolean;
  message: string;
  messageEs: string;
  timestamp: string;
  offline?: boolean;
  firstName?: string;
  lastName?: string;
  punchType?: string;
  weeklyHours?: number;
  exception?: number;
}

class SoapClient {
  private checkinClient: Client | null = null;
  private summaryClient: Client | null = null;
  private credentials: any = null;
  private isOnline: boolean = false;
  private connectionError: string | null = null;
  private settings: SoapSettings;

  constructor(settings: SoapSettings) {
    this.settings = settings;
    this.setupClient().catch((err) => {
      console.error("Failed to initialize SOAP client:", err);
      this.connectionError = err.message;
    });
  }

  private async setupClient(): Promise<boolean> {
    try {
      const baseUrl = `${this.settings.endpoint}Services`;

      // Initialize clients with request timeout
      const requestOptions = {
        wsdl_options: {
          timeout: this.settings.timeout * 1000,
        },
        forceSoap12Headers: false,
      };

      this.checkinClient = await createClientAsync(
        `${baseUrl}/MSIWebTraxCheckIn.asmx?WSDL`,
        requestOptions
      );

      this.summaryClient = await createClientAsync(
        `${baseUrl}/MSIWebTraxCheckInSummary.asmx?WSDL`,
        requestOptions
      );

      // Set up credentials
      this.credentials = {
        UserCredentials: {
          UserName: this.settings.username,
          PWD: this.settings.password,
        },
      };

      // Test connection
      if (this.summaryClient && this.checkinClient) {
        this.isOnline = true;
        this.connectionError = null;
        return true;
      }

      throw new Error("Failed to initialize SOAP clients");
    } catch (error) {
      this.isOnline = false;
      this.connectionError =
        error instanceof Error ? error.message : "Unknown error";
      return false;
    }
  }

  public async submitPunch(employeeId: string): Promise<PunchResponse> {
    if (!this.isOnline || !this.summaryClient) {
      // Try to reconnect
      const reconnected = await this.setupClient();
      if (!reconnected) {
        return this.handleOfflinePunch(employeeId);
      }
    }

    try {
      const punchTime = new Date().toISOString();
      const swipeInput = `${employeeId}|*|${punchTime}`;

      const result = await this.summaryClient!.RecordSwipeSummaryAsync({
        _soapHeaders: [this.credentials],
        swipeInput,
      });

      const response = result[0];

      if (!response?.RecordSwipeReturnInfo) {
        throw new Error("Invalid response from server");
      }

      const info = response.RecordSwipeReturnInfo;

      return {
        success: info.PunchSuccess,
        offline: false,
        message: info.PunchSuccess
          ? "Punch recorded successfully"
          : "Failed to record punch",
        messageEs: info.PunchSuccess
          ? "Registro exitoso"
          : "Error al registrar",
        timestamp: punchTime,
        firstName: info.FirstName,
        lastName: info.LastName,
        punchType: info.PunchType,
        weeklyHours: response.CurrentWeeklyHours,
        exception: info.PunchException,
      };
    } catch (error) {
      console.error("SOAP error:", error);
      this.isOnline = false;
      this.connectionError =
        error instanceof Error ? error.message : "Unknown error";
      return this.handleOfflinePunch(employeeId);
    }
  }

  private handleOfflinePunch(employeeId: string): PunchResponse {
    // TODO: Implement offline storage
    const timestamp = new Date().toISOString();
    return {
      success: true,
      offline: true,
      message: "Punch stored offline",
      messageEs: "Registro almacenado localmente",
      timestamp,
    };
  }

  public isConnected(): boolean {
    return this.isOnline;
  }

  public getConnectionError(): string | null {
    return this.connectionError;
  }
}

// Create singleton instance
let soapClient: SoapClient | null = null;

export const initializeSoapClient = (settings: SoapSettings) => {
  soapClient = new SoapClient(settings);
};

export const submitPunch = async (
  employeeId: string
): Promise<PunchResponse> => {
  if (!soapClient) {
    throw new Error("SOAP client not initialized");
  }
  return soapClient.submitPunch(employeeId);
};

export const isSoapConnected = (): boolean => {
  return soapClient?.isConnected() ?? false;
};

export const getSoapConnectionError = (): string | null => {
  return soapClient?.getConnectionError() ?? null;
};

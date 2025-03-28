declare module "*.json" {
  const settings: {
    soap: {
      username: string;
      password: string;
      endpoint: string;
      timeout: number;
      clientId: number;
    };
    storage: {
      retentionDays: number;
      maxOfflineRecords: number;
    };
  };
  export default settings;
}

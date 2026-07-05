import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as SonnerToaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import Workstation from "@/pages/Workstation";

const queryClient = new QueryClient();

function App() {
  if (typeof document !== 'undefined') {
    document.documentElement.classList.add('dark');
  }

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Workstation />
        <Toaster />
        <SonnerToaster position="bottom-center" richColors />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;

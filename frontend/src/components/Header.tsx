import { useAuth } from "@/contexts/AuthContext";
import { ProfileMenu } from "./ProfileMenu";

export default function Header() {
  const { user, authenticated } = useAuth();
  
  // Get first name from the authenticated user
  const firstName = user?.name?.split(' ')[0] || '';
  
  return (
    <>
      {/* Header - Fixed */}
      <div className="px-10 py-6 flex-shrink-0 bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto flex flex-row justify-between">
          <h1 className="text-2xl font-bold font-serif text-gray-700">
            {authenticated && firstName ? `Hey there, ${firstName}.` : "Hey there."}
          </h1>
          <ProfileMenu />
        </div>
      </div>
    </>
  );
}

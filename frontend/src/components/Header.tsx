interface User {
  id: string;
  username: string;
}

interface Props {
  user: User | undefined;
}

export default function Header({ user }: Props) {
  return (
    <>
      {/* Header - Fixed */}
      <div className="px-10 py-6 flex-shrink-0 bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold font-serif text-gray-700">
            {user ? `Hey there, ${user.username}.` : "Hey there."}
          </h1>
        </div>
      </div>
    </>
  );
}

import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send, FileText, MessageSquare, BookOpen, ChevronLeft, ChevronRight, Save, FolderOpen, FolderPlus, Trash2, Check, ChevronDown } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import Layout from '../components/Layout';
import Sidebar from '../components/Sidebar';
import { papersApi, collectionsApi, tasksApi } from '../api/services';
import { Paper, ChatMessage, Note, Collection, Task } from '../types';
import clsx from 'clsx';

const ReadingRoomPage: React.FC = () => {
  const { paperId } = useParams<{ paperId: string }>();
  const navigate = useNavigate();
  const [paper, setPaper] = useState<Paper | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [notes, setNotes] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);
  const [activeTab, setActiveTab] = useState<'chat' | 'notes' | 'collections'>('chat');
  const chatEndRef = useRef<HTMLDivElement>(null);
  
  // Resizable Panel State
  const [rightPanelWidth, setRightPanelWidth] = useState(384); // Default 96 (384px)
  const [isResizing, setIsResizing] = useState(false);
  const isDraggingRef = useRef(false);

  // Collections State
  const [allCollections, setAllCollections] = useState<Collection[]>([]);
  const [paperCollections, setPaperCollections] = useState<Collection[]>([]);
  const [loadingCollections, setLoadingCollections] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState('');

  // Navigator State
  // Moved to Sidebar
  
  // Fetch Paper Data
  useEffect(() => {
    if (!paperId) return;

    const fetchData = async () => {
      try {
        const [paperData, history, notesData] = await Promise.all([
          papersApi.get(paperId),
          papersApi.getChatHistory(paperId),
          papersApi.getNotes(paperId)
        ]);
        setPaper(paperData);
        setMessages(history || []); // Ensure array
        setNotes(notesData?.content || '');
      } catch (error) {
        console.error('Failed to load paper data:', error);
      }
    };
    fetchData();
    fetchCollections();
  }, [paperId]);

  // Fetch Collections
  const fetchCollections = async () => {
      try {
          const cols = await collectionsApi.list();
          setAllCollections(cols);
          if (paperId) {
              const pCols = await collectionsApi.getPaperCollections(paperId);
              setPaperCollections(pCols);
          }
      } catch (error) {
          console.error("Failed to fetch collections", error);
      }
  };

  const toggleTaskExpand = (taskId: string) => {
      // Deprecated, logic moved to Sidebar
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activeTab]);

  const handleSend = async () => {
    if (!paperId || !input.trim() || sending) return;
    
    const userMsg: ChatMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setSending(true);
    
    try {
      const response = await papersApi.chat(paperId, userMsg.content);
      setMessages(prev => [...prev, response]);
    } catch (error) {
      console.error('Chat failed:', error);
    } finally {
      setSending(false);
    }
  };

  const handleSaveNotes = async () => {
    if (!paperId) return;
    setSavingNotes(true);
    try {
      await papersApi.updateNotes(paperId, notes);
    } catch (error) {
      console.error('Failed to save notes:', error);
    } finally {
      setSavingNotes(false);
    }
  };

  const handleCreateCollection = async () => {
      if (!newCollectionName.trim()) return;
      try {
          await collectionsApi.create(newCollectionName);
          setNewCollectionName('');
          fetchCollections();
      } catch (e) {
          console.error(e);
      }
  };

  const toggleCollection = async (collectionId: string, has: boolean) => {
      if (!paperId) return;
      try {
          if (has) {
              await collectionsApi.removePaper(collectionId, paperId);
          } else {
              await collectionsApi.addPaper(collectionId, paperId);
          }
          // Refresh paper collections
          const pCols = await collectionsApi.getPaperCollections(paperId);
          setPaperCollections(pCols);
      } catch (e) {
          console.error(e);
      }
  };

  const handleDeleteCollection = async (id: string, e: React.MouseEvent) => {
      e.stopPropagation();
      if (!window.confirm("Delete this collection?")) return;
      try {
          await collectionsApi.delete(id);
          fetchCollections();
      } catch (error) {
          console.error("Failed to delete collection", error);
      }
  };

  const handleCreateSubCollection = async (parentId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      const name = window.prompt("Enter name for sub-collection:");
      if (!name || !name.trim()) return;
      
      try {
          await collectionsApi.create(name, parentId);
          fetchCollections();
      } catch (error) {
          console.error("Failed to create sub-collection", error);
      }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    isDraggingRef.current = true;
    setIsResizing(true);
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'col-resize';
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDraggingRef.current) return;
    const newWidth = window.innerWidth - e.clientX;
    // Limit width (min 300, max 800)
    if (newWidth >= 300 && newWidth <= 800) {
      setRightPanelWidth(newWidth);
    }
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
    setIsResizing(false);
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'default';
  };

  const renderCollectionTree = (collections: Collection[], activeCollections: Collection[], parentId: string | null = null, level = 0) => {
      // Filter for current level
      const nodes = collections.filter(c => {
          if (parentId) return c.parent_id === parentId;
          return !c.parent_id || c.parent_id === ''; // Root nodes have null or empty parent_id
      });
      
      return nodes.map(node => (
          <div key={node.id}>
              {renderCollectionItem(node, activeCollections, level)}
              {/* Recursive call for children */}
              <div className="ml-4 border-l border-gray-100 pl-2">
                  {renderCollectionTree(collections, activeCollections, node.id, level + 1)}
              </div>
          </div>
      ));
  };

  const renderCollectionItem = (col: Collection, activeCollections: Collection[], level: number) => {
      const isAdded = activeCollections.some(c => c.id === col.id);
      return (
        <div key={col.id} className={clsx("flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 group")}>
            <div className="flex items-center gap-3 overflow-hidden">
                <FolderOpen size={18} className="text-blue-500 shrink-0" />
                <span className="text-sm text-gray-700 truncate" title={col.name}>{col.name}</span>
            </div>
            <div className="flex items-center gap-2">
                <button
                    onClick={(e) => handleCreateSubCollection(col.id, e)}
                    className="p-1 text-gray-400 hover:text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Add Sub-collection"
                >
                    <FolderPlus size={14} />
                </button>
                <button
                    onClick={(e) => handleDeleteCollection(col.id, e)}
                    className="p-1 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Delete Collection"
                >
                    <Trash2 size={14} />
                </button>
                <button 
                    onClick={() => toggleCollection(col.id, isAdded)}
                    className={clsx(
                        "w-5 h-5 flex items-center justify-center rounded border transition-colors shrink-0",
                        isAdded ? "bg-blue-600 border-blue-600 text-white" : "border-gray-300 text-transparent hover:border-blue-400"
                    )}
                >
                    <Check size={12} />
                </button>
            </div>
        </div>
      );
  };

  if (!paper) return <Layout><div>Loading...</div></Layout>;

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
        <Sidebar />
        
        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0">
            <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shrink-0">
                <div className="min-w-0 flex-1">
                    <h1 className="font-semibold text-gray-900 truncate max-w-xl" title={paper.title}>
                        {paper.title}
                    </h1>
                </div>
                <div className="flex gap-2 shrink-0">
                    <button 
                        onClick={() => setActiveTab('chat')}
                        className={clsx("px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2", activeTab === 'chat' ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100")}
                    >
                        <MessageSquare size={16} /> Chat
                    </button>
                    <button 
                        onClick={() => setActiveTab('notes')}
                        className={clsx("px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2", activeTab === 'notes' ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100")}
                    >
                        <FileText size={16} /> Notes
                    </button>
                    <button 
                        onClick={() => setActiveTab('collections')}
                        className={clsx("px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2", activeTab === 'collections' ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100")}
                    >
                        <FolderOpen size={16} /> Collections
                    </button>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* PDF Viewer */}
                <div className="flex-1 border-r border-gray-200 bg-gray-200 flex flex-col relative">
                    {paper.pdf_path ? (
                        <>
                            <iframe 
                                src={`http://localhost:8000/api/pdfs/${paper.task_id}/${paper.id}.pdf`}
                                className={clsx("w-full h-full", isResizing && "pointer-events-none select-none")}
                                title="PDF Viewer"
                            />
                            {/* Overlay to catch events during resize */}
                            {isResizing && <div className="absolute inset-0 z-50 bg-transparent" />}
                        </>
                    ) : (
                        <div className="flex items-center justify-center h-full text-gray-500">
                            PDF not available
                        </div>
                    )}
                </div>

                {/* Resizer Handle */}
                <div 
                    className="w-1 bg-gray-200 hover:bg-blue-400 cursor-col-resize transition-colors flex items-center justify-center z-20"
                    onMouseDown={handleMouseDown}
                >
                    <div className="h-8 w-1 bg-gray-400 rounded-full opacity-50" />
                </div>

                {/* Right Panel (Chat/Notes/Collections) */}
                <div style={{ width: rightPanelWidth }} className="flex flex-col bg-white shrink-0 border-l border-gray-200">
                    {activeTab === 'chat' && (
                        <>
                            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                                {messages.length === 0 && (
                                    <div className="text-center text-gray-400 text-sm mt-10">
                                        No messages yet. Ask something about the paper!
                                    </div>
                                )}
                                {messages.map((msg, idx) => (
                                    <div key={idx} className={clsx("flex", msg.role === 'user' ? "justify-end" : "justify-start")}>
                                        <div className={clsx(
                                            "max-w-[90%] rounded-2xl px-4 py-3 text-sm relative group",
                                            msg.role === 'user' 
                                                ? "bg-blue-600 text-white rounded-br-none" 
                                                : "bg-gray-100 text-gray-800 rounded-bl-none"
                                        )}>
                                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                                            {msg.role === 'assistant' && (msg.cost !== undefined || msg.time_cost !== undefined) && (
                                                <div className="mt-2 pt-2 border-t border-gray-200/50 flex gap-3 text-[10px] text-gray-400 font-mono">
                                                    {msg.cost !== undefined && (
                                                        <span>Cost: ${msg.cost.toFixed(6)}</span>
                                                    )}
                                                    {msg.time_cost !== undefined && (
                                                        <span>Time: {msg.time_cost.toFixed(2)}s</span>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                                {sending && (
                                    <div className="flex justify-start">
                                        <div className="bg-gray-100 rounded-2xl px-4 py-3 text-sm rounded-bl-none text-gray-500 animate-pulse">
                                            Thinking...
                                        </div>
                                    </div>
                                )}
                                <div ref={chatEndRef} />
                            </div>
                            <div className="p-4 border-t border-gray-200">
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={input}
                                        onChange={(e) => setInput(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                                        placeholder="Ask about the paper..."
                                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        disabled={sending}
                                    />
                                    <button
                                        onClick={handleSend}
                                        disabled={sending || !input.trim()}
                                        className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                                    >
                                        <Send size={20} />
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                    
                    {activeTab === 'notes' && (
                        <div className="flex-1 flex flex-col">
                            <div className="flex-1 p-4">
                                <textarea
                                    value={notes}
                                    onChange={(e) => setNotes(e.target.value)}
                                    className="w-full h-full resize-none border-none focus:ring-0 text-gray-800"
                                    placeholder="Write your notes here..."
                                />
                            </div>
                            <div className="p-4 border-t border-gray-200 flex justify-end">
                                <button
                                    onClick={handleSaveNotes}
                                    disabled={savingNotes}
                                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                                >
                                    <Save size={18} /> {savingNotes ? 'Saving...' : 'Save Notes'}
                                </button>
                            </div>
                        </div>
                    )}

                    {activeTab === 'collections' && (
                        <div className="flex-1 flex flex-col p-4">
                            <h3 className="text-sm font-semibold text-gray-700 mb-4">Manage Collections</h3>
                            
                            <div className="flex gap-2 mb-6">
                                <input 
                                    type="text" 
                                    value={newCollectionName}
                                    onChange={e => setNewCollectionName(e.target.value)}
                                    placeholder="New collection..."
                                    className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg"
                                />
                                <button 
                                    onClick={handleCreateCollection}
                                    className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded-lg"
                                    title="Create Collection"
                                >
                                    <FolderPlus size={18} />
                                </button>
                            </div>

                            <div className="space-y-2 overflow-y-auto flex-1">
                                {allCollections.length === 0 && (
                                    <p className="text-sm text-gray-400 text-center">No collections created yet.</p>
                                )}
                                {renderCollectionTree(allCollections, paperCollections)}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    </div>
  );
};

export default ReadingRoomPage;

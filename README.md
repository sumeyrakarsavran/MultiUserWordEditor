Multi-User Real-Time Text Editor

**1\. INTRODUCTION**

**Objective:**  
In this project, a system was developed that allows multiple users to work on text files simultaneously. The system consists of a WebSocket server and tkinter GUI-based clients.

**Technologies:**

- Python
- websockets (WebSocket protocol)
- tkinter (GUI)
- Asyncio (Asynchronous Programming)
- JSON (data exchange)


**2\. SYSTEM ARCHITECTURE**

**2.1 General Structure:**

+------------------+ WebSocket +------------------+

| Client 1 | &lt;--------------------&gt; | Server |

+------------------+ +------------------+

↑                             ↑

+------------------+ +------------------+

| Client 2 | &lt;--------------------&gt; | File System |

+------------------+ +------------------+

**2.2 Components:**

| **Component** | **Explanation** |
| --- | --- |
| **Server** | It manages all files. Saves and publishes changes. |
| **Client** | It offers an interface to the user. It provides operations such as file creation and editing. |
| **File System** | Files are stored in the server_files/ directory. The server writes the file to disk with each update. |

**3\. SERVER APPLICATION**

**Key Duties:**

- Listens for WebSocket connections
- Creates, deletes and lists files
- Publishes changes made to a file to all users
- Save/upload files to the server directory

**Data Structures:**

| **Variable** | **Explanation** |
| --- | --- |
| clients | Maintains WebSocket connections and each client's open file/username |
| files | File names and contents are stored as a dictionary |

**Operation Diagram (Server):**

Client sends message ── ▶ JSON is resolved ── ▶

│                        │

├─ ▶ "set_username" ├─ ▶ Username is stored

├─ ▶ "list_files" ├─ ▶ File list is sent

├─ ▶ "create_file" ├─ ▶ File is created, written to disk

├─ ▶ "delete_file" ├─ ▶ File deleted, published

└─ ▶ "insert"/"delete" └─ ▶ Text is updated, written to disk, and propagated

**4\. CLIENT APP**

**Key Duties:**

- Retrieves the username from the user
- Shows the list of files
- Shows the contents of the selected file
- Notifies the server of keyboard changes made
- Takes the changes made by other users and reflects them in the application

**Interface Features:**

| **Component** | **Function** |
| --- | --- |
| Listbox | Shows the list of files on the server |
| Text | Shows the contents of the active file and allows editing |
| Button | Used for file creation and deletion |

**Functioning Diagram (Client):**

User interaction ── ▶ Event Handler (GUI)

│

├─ ▶ File selection ── ▶ open_file request

├─ ▶ Keyboard key ── ▶ insert/delete request

├─ ▶ Buttons ── ▶ create/delete_file request

▼

Incoming messages are asynced and transferred to the GUI thread

**5\. MESSAGE STRUCTURES (JSON)**

| **Action** | **Sender** | **Area** | **Explanation** |
| --- | --- | --- | --- |
| set_username | Client | Server | Reports username |
| list_files | Client | Server | Requests the file list |
| files_list | Server | Client | Sends existing files |
| create_file | Client | Server | Creates a new file |
| delete_file | Client | Server | File deletion request |
| open_file | Client | Server | Requests file contents |
| file_content | Server | Client | Sends file contents |
| insert | Client | Server & Other Clients | Instructs the addition of characters to the content |
| Delete | Client | Server & Other Clients | Deletes specific characters |

**6\. OPERATING PRINCIPLES**

**6.1 States**

| **State** | **Explanation** |
| --- | --- |
| Disconnected | WebSocket connection not yet established |
| Connected | WebSocket connection established, username not sent |
| LoggedIn | Username submitted, server file list may return |
| FileSelected | A file is selected, its contents are retrieved |
| Editing | User editing text, submitting changes |

**6.2 Transitions**

| **Event** | **Source Status** | **Target Situation** | **Explanation** |
| --- | --- | --- | --- |
| connect() | Disconnected | Connected | WebSocket connection established |
| send_username() | Connected | LoggedIn | Username submitted |
| list_files() | LoggedIn | LoggedIn | File list retrieved from server |
| select_file() | LoggedIn | FileSelected | File selected, content retrieved |
| edit_text() | FileSelected | Editing | User added/deleted text |
| receive_edit() | FileSelected/Editing | Editing | Changes made by other users were taken |
| disconnect() | _Any State_ | Disconnected | Connection broken/closed |

**6.3 FSM Diagram**

<img width="312" height="483" alt="fsm" src="https://github.com/user-attachments/assets/6fec20ff-73ce-4ea1-95ab-e221c394ba07" />

**6.4 FSM Mermaid Notation**

stateDiagram-v2

\[\*\] --> Disconnected

Disconnected --> Connected: connect()

Connected --> LoggedIn: send_username()

LoggedIn --> LoggedIn: list_files()

LoggedIn --> FileSelected: select_file()

FileSelected --> Editing: edit_text()

Editing --> Editing: receive_edit()

FileSelected --> Editing: receive_edit()

Disconnected &lt;--&gt; \[\*\]: disconnect()

**6.5 Protocol Message Types and Transaction Table**

| **Message Type (action)** | **Sender** | **Buyer** | **Message Content** | **Buyer's Action** |
| --- | --- | --- | --- | --- |
| set_username | Client | Server | { "action": "set_username", "username": "John" } | Defines the user to the clients dictionary. |
| list_files | Client | Server | { "action": "list_files" } | files_list returns the list of files with the message. |
| files_list | Server | Client | { "action": "files_list", "files": \["a.txt", "b.txt"\] } | Updates the list box on the interface. |
| create_file | Client | Server | { "action": "create_file", "filename": "yeni.txt" } | files list, writes to disk, files_list paths to all clients. |
| delete_file | Client | Server | { "action": "delete_file", "filename": "sil.txt" } | files list, removes the file on the disk, publishes files_list message. |
| open_file | Client | Server | { "action": "open_file", "filename": "a.txt" } | It finds the file contents, sends file_content message to the client. |
| file_content | Server | Client | { "action": "file_content", "filename": "a.txt", "content": "..." } | Populates the Text field with incoming content. |
| insert | Client | Server | { "action": "insert", "filename": "a.txt", "index": "2.5", "content": "a" } | Adds content to the specified location, saves the file, sends the message to other clients. |
| Delete | Client | Server | { "action": "delete", "filename": "a.txt", "index": "2.5", "length": 1 } | Deletes the character(s) in the specified location, saves them, sends them to other clients. |
| insert | Server | Client | { "action": "insert", "filename": "a.txt", "index": "2.5", "content": "a" } | If the open file matches, it adds to the client's interface. |
| Delete | Server | Client | { "action": "delete", "filename": "a.txt", "index": "2.5", "length": 1 } | If the open file matches, the client deletes the corresponding character(s). |
| ConnectionClosed | \-  | \-  | \-  | Server: removes from the list of clients.  <br>Client: The GUI continues to work, but the connection is lost. |

**6.6 Basic Principle of Compatible Communication of Two End Systems Without Knowing Coding**

1. The parties do not know how each other works.
    - For example, the client doesn't know how the server stores files.
    - The server also does not know how the client's GUI is drawn.
2. They both only implement the protocol.
    - The client sends a "create_file" message.
    - The server only checks that the message is "action": "create_file" and takes the necessary action.
3. Mutual understanding guarantee:
    - Thanks to the use of JSON, every domain ("filename", "content") is open and fixed.
    - Both parties act according to these areas and do not comment on what the data in the content is.

**6.7 Protocol Flow: Diagram Symbol Representation**

+-----------------+ +----------------+

| Client | | Server |

+-----------------+ +----------------+

| |

|--- set_username ---------->| Start a session

|--- list_files -------------->| Request file list

| |

|<-- files_list --------------| Get the list

|--- create_file ------------>| Create a file

| |

|<-- files_list -------------- | Current list

|--- open_file -------------->| Request file content

|<-- file_content ------------| Get content

| |

|--- insert / delete -------->| Make arrangements

|<-- insert / delete ---------| Spread to other clients

| |

|--- delete_file ------------>| Delete file

|<-- files_list --------------| Current list

**7\. SECURITY AND RESTRICTIONS**

- Users can't see each other's IDs (only content syncs)
- There may be some race cases in simultaneous writing (line-based analysis can be applied)

**8\. DEVELOPMENT SUGGESTIONS**

- **Username Representation:** Username can be displayed in every edit.
- **Versioning:** File versions can be stored.
- **Access Authorizations:** Special file permissions can be added to each user.

**9\. CONCLUSION**

This project is very fruitful in terms of experiencing the process of developing a real-time collaboration application with WebSocket and demonstrating how technologies such as asyncio and tkinter can work together. It is a structure that can form the basis for scenarios such as different users working on a document simultaneously.

**10\. SCREENSHOTS & PRINTOUTS**

Usage

<img width="1920" height="1080" alt="Screenshot 2025-06-22 180827" src="https://github.com/user-attachments/assets/b9a16c20-4fa4-4ec6-97ce-6ad3497ea030" />
Connecting to the server
<img width="1920" height="1080" alt="Screenshot 2025-06-06 231420" src="https://github.com/user-attachments/assets/a2048e4a-c9bb-4e2b-bf42-c1c8961e6f5e" />
The screens that appear after executing the client code are shown. When you type a username, the text editor screen is active.
<img width="1920" height="1020" alt="Screenshot 2025-06-06 231436" src="https://github.com/user-attachments/assets/0028478f-91c0-4434-8cf5-fc2228008e8b" />
Enter the username and click on the arrow.
<img width="1920" height="1020" alt="Screenshot 2025-06-06 231558" src="https://github.com/user-attachments/assets/da24297b-977f-4dc3-ae4f-ca55bb63acb2" />


Documents

<img width="796" height="158" alt="Screenshot 2025-06-22 204217" src="https://github.com/user-attachments/assets/ee9d1678-4ac8-4902-a9cf-f0e6c0ee47f0" />
<img width="827" height="307" alt="Screenshot 2025-06-22 204228" src="https://github.com/user-attachments/assets/87530308-7d26-43c8-956a-428f1977428e" />
<img width="757" height="378" alt="Screenshot 2025-06-22 204413" src="https://github.com/user-attachments/assets/fa478acd-4586-414f-8301-0bf17a8da728" />



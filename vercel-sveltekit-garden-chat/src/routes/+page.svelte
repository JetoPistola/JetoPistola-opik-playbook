<script lang="ts">
  import { Chat } from "@ai-sdk/svelte";
  import { DefaultChatTransport } from "ai";

  // One Chat instance = one conversation = one Opik thread (its id is sent on every turn).
  const chat = new Chat({ transport: new DefaultChatTransport({ api: "/api/chat" }) });
  let input = $state("");

  function send(event: SubmitEvent) {
    event.preventDefault();
    if (!input.trim()) return;
    chat.sendMessage({ text: input });
    input = "";
  }
</script>

<main>
  <h1>Sprout, the Fernhollow garden helper</h1>
  {#each chat.messages as message (message.id)}
    <p class={message.role}>
      <strong>{message.role === "user" ? "You" : "Sprout"}:</strong>
      {#each message.parts as part}{#if part.type === "text"}{part.text}{/if}{/each}
    </p>
  {/each}
  <form onsubmit={send}>
    <input bind:value={input} placeholder="Ask about tomatoes, slugs, garlic..." disabled={chat.status !== "ready"} />
    <button disabled={chat.status !== "ready"}>Send</button>
  </form>
</main>

<style>
  main { max-width: 36rem; margin: 2rem auto; font-family: system-ui, sans-serif; padding: 0 1rem; }
  .user { color: #2b5d34; }
  form { display: flex; gap: 0.5rem; margin-top: 1rem; }
  input { flex: 1; padding: 0.5rem; }
</style>

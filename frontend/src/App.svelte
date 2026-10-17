<script lang="ts">
  import Sidebar from './components/Sidebar.svelte'
  import { getInfo } from './lib/api'
  import { route } from './lib/router.svelte'
  import FunctionLab from './pages/FunctionLab.svelte'
  import Guide from './pages/Guide.svelte'
  import Knapsack from './pages/Knapsack.svelte'

  let name = $state('')
  let version = $state('')

  $effect(() => {
    getInfo()
      .then((info) => {
        name = info.name
        version = info.version
      })
      .catch(() => {})
  })

  let main: HTMLElement | undefined = $state()

  $effect(() => {
    // A new page starts at its top
    void route.path
    main?.scrollTo(0, 0)
  })
</script>

<div class="shell">
  <Sidebar {name} {version} />
  <main bind:this={main}>
    <div class="page">
      {#if route.path === '/knapsack'}
        <Knapsack />
      {:else if route.path === '/function'}
        <FunctionLab />
      {:else}
        <Guide />
      {/if}
    </div>
  </main>
</div>

<style>
  .shell {
    display: flex;
    height: 100vh;
    overflow: hidden;
  }
  main {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
  }
  .page {
    max-width: 1400px;
    margin: 0 auto;
    padding: 1.8rem 2rem 4rem;
  }
  @media (max-width: 700px) {
    .shell {
      flex-direction: column;
    }
    .page {
      padding: 1rem 1rem 3rem;
    }
  }
</style>

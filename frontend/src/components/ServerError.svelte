<script lang="ts">
  let { error }: { error: string } = $props()
</script>

<p class="error">
  The server did not answer: {error}. Start it with
  <code>uv run python -m genetic_opt.web.app</code>.
</p>

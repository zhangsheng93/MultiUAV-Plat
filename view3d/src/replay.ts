export class ReplayState {
  live = true;
  trailLength = 80;

  setLive(live: boolean): void {
    this.live = live;
  }

  setTrailLength(length: number): void {
    this.trailLength = Math.max(2, Math.min(200, Math.round(length)));
  }
}

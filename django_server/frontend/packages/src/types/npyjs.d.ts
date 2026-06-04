declare module 'npyjs' {
  export default class Npyjs {
    load(
      filename: string | ArrayBuffer,
      callback?: (result: { data: Float32Array; shape: number[] }) => void,
    ): Promise<{ data: Float32Array; shape: number[] }>;
  }
}

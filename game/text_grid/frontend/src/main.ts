import './style.css';
import { Scene, Game, WEBGL, GameObjects} from 'phaser';



const canvas = document.getElementById('game') as HTMLCanvasElement;

const ORIGIN_X = 100
const ORIGIN_Y = 100

class GameScene extends Scene {
  private readonly gridWidth = 100;
  private readonly gridHeight = 100;
  private readonly squareSize = 5;
  private gridGraphics!: GameObjects.Graphics;
  private square!: GameObjects.Sprite;
  // Declare a variable named mydata of any type
  private mydata: any;



  private currentCol = 1;
  private currentRow = 1;

  constructor() {
    super('scene-game');
  }

  async load_file(){
    const response = await fetch('http://localhost:5001/read_file?file_path=alice_home/environment.json');
    console.log(response);
    const data = await response.json();
    this.mydata = data['message'];
    return Promise.resolve();
  }

  preload() {
    this.load.image('object', 'assets/square.png');
  }

  getRandomColor(): number {
    // Generate a random 24-bit number
    const color = Math.floor(Math.random() * 0xffffff);
  
    return color;
  }
    
  async create_scene(){
    await this.load_file();

    console.log(this.mydata)

    this.lastTime = 0;


    this.gridGraphics = this.add.graphics();

    console.log(this.mydata.areas);

    this.gridGraphics.lineStyle(5, 0x080808, 1.0);
    this.gridGraphics.strokeRect(
      ORIGIN_X - this.squareSize / 2 - 4,
      ORIGIN_Y - this.squareSize / 2 - 4,
      this.mydata.size[0] * this.squareSize + 8,
      this.mydata.size[1] * this.squareSize + 8
    );


    let areas_key = Object.keys(this.mydata.areas)
    for (let i=0; i < areas_key.length; i++){
      let area_key = areas_key[i]
      let area = this.mydata.areas[area_key];
      let randomcolor = this.getRandomColor()
      console.log(randomcolor)
      
      if (area.hasOwnProperty('color')) {
        this.gridGraphics.fillStyle(parseInt(area['color'], 16), 1);
      } else {
        this.gridGraphics.fillStyle(0xffffff, 1);
      }

      this.gridGraphics.fillRect(
        ORIGIN_X - this.squareSize /2 + this.squareSize * (area.location[0][0] -1),
        ORIGIN_Y - this.squareSize / 2+ this.squareSize * (area.location[0][1] -1),
        (area.location[1][0] - area.location[0][0] + 1)* this.squareSize,
        (area.location[1][1] - area.location[0][1] + 1 )* this.squareSize
      );
      // Add the text in the middle of the strokeRect, with the text value of area.name
      this.add.text(
        100 - this.squareSize /2 + this.squareSize * (area.location[0][0] -1) + ((area.location[1][0] - area.location[0][0] )* this.squareSize)/2,
        100 - this.squareSize / 2+ this.squareSize * (area.location[0][1] -1) + ((area.location[1][1] - area.location[0][1] )* this.squareSize)/2,
        area.name,
        {
          font: '15px Arial',
          fill: '#000000',
          border: null
        }
      );
    }
  }

  async place_objects(){
    await this.load_file();
    // Loop through each object in mydata.objects

    let objects_key = Object.keys(this.mydata.objects)
    for (let i=0; i < objects_key.length; i++){
      let object_key = objects_key[i]
      let obj = this.mydata.objects[object_key];

      console.log("obj", obj)

      let obj_x = obj.location[0] + this.mydata.areas[obj.eid].location[0][0]
      let obj_y = obj.location[1] + this.mydata.areas[obj.eid].location[0][1]

      console.log("obj_x, obj_y", obj_x, obj_y)
      // Check if the object already exists in the scene
      let existingObj = this.children.getByName(obj.id);
      if (existingObj) {
        // If the object already exists, update its location
        existingObj.x = ORIGIN_X + obj_x * this.squareSize - this.squareSize / 2;
        existingObj.y = ORIGIN_Y + obj_y * this.squareSize - this.squareSize / 2;
        let existingObj_title = this.children.getByName(obj.id+"_title");
        existingObj_title.x = existingObj.x;
        existingObj_title.y = existingObj.y;
      } else {
        console.log("Here", obj)
        
        // If the object does not exist, create a new sprite for it
        let newObj = this.add.sprite(
          ORIGIN_X + obj_x * this.squareSize  - this.squareSize / 2,
          ORIGIN_Y + obj_y * this.squareSize  - this.squareSize / 2,
          'object'
        );

        newObj.setScale(this.squareSize / 30);
        newObj.setName(object_key);
        // Change the color of the sprite to white
        newObj.setTint(0xffffff);
        // Add text to the sprite with the value of obj.name
        let obj_title = this.add.text(
          newObj.x,
          newObj.y,
          obj.name,
          {
            font: '15px Arial',
            fill: '#000000',
            backgroundColor: '#ffffff',
            padding: 5
          }
        );
        obj_title.setName(object_key+"_title");


      }
    }
  }


  create() {
    this.lastTime = 0.0
    this.create_scene()
    this.place_objects()

  }

    /// Use the update() function to update the square's position every 1 second to the left
  update(time, delta) {
      // Set the scene's time event to update the square's position every 1 second to the left
      if (time > this.lastTime + 1000) {
        console.log("update!")
        this.place_objects()
        this.lastTime = time
      }
  }
}

const config = {
  type: WEBGL,
  width: window.innerWidth,
  height: window.innerHeight,
  canvas,
  physics: {
    default: 'arcade',
    arcade: {
      gravity: { y: 0 },
      // debug: true
    }
  },
  backgroundColor: '#ffffff',
  scene: [GameScene]
};

new Game(config);

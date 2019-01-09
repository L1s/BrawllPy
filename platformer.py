""" Tilengine python platformer demo """
# pylint: disable=C0103
# pylint: disable=W0614
# pylint: disable=W0312
# import os
# os.environ["PYSDL2_DLL_PATH"] = "C:\\Users\\LM\\Desktop\\PySDL2-0.9.5"

import xml.etree.ElementTree as ET
from math import sin, radians
from tilengine import *
#from sound import Sound #mac/linux sound 
import winsound # windows sound


# constants
WIDTH = 680
HEIGHT = 360
ASSETS_PATH = "assets"
SKY_COLORS = (Color.fromstring("#78D7F2"), Color.fromstring("#E2ECF2"))

def load_objects(file_name, layer_name, first_gid):
	""" loads tiles in object layer from a tmx file.
	Returns list of Item objects """
	tree = ET.parse(file_name)
	root = tree.getroot()
	for child in root.findall("objectgroup"):
		name = child.get("name")
		if name == layer_name:
			item_list = list()
			for item in child.findall("object"):
				gid = item.get("gid")
				if gid is not None:
					x = item.get("x")
					y = item.get("y")
					x = int(float(x))
					y = int(float(y))
					item_list.append(Item(int(gid) - first_gid, x, y))
			return item_list
	return None

# Game management definitions *************************************************


class State:
	""" player states """
	Undefined, Idle, Run, Jump, Hit = range(5)

class Direction:
	""" player orientations """
	Right, Left = range(2)

class Tiles:
	""" types of tiles for sprite-terrain collision detection """
	Empty, Floor, Gem, Wall, SlopeUp, SlopeDown, InnerSlopeUp, InnerSlopeDown = range(8)

class Medium:
	""" types of environments """
	Floor, Air, Ladder, Water = range(4)

class Rectangle(object):
	""" aux rectangle """
	def __init__(self, x, y, w, h):
		self.width = w
		self.height = h
		self.update_position(x, y)

	def update_position(self, x, y):
		self.x1 = x
		self.y1 = y
		self.x2 = x + self.width
		self.y2 = y + self.height

	def check_point(self, x, y):
		""" returns if point is contained in rectangle """
		return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

class Item(object):
	""" Generic item declared in tilemap object layer awaiting to spawn """
	Opossum, Eagle, Cristal = range(3)
	def __init__(self, item_type, x, y):
		self.type = item_type
		self.x = x
		self.y = y
		self.alive = False

	def try_spawn(self, x):
		""" Tries to spawn an active game object depending on screen position and item type """
		
		if self.alive is False:
			self.alive = True
			if self.type is Item.Eagle:
				# print("Trying to spawn eagle")
				Eagle(self, self.x, self.y - Eagle.size[1])
			elif self.type is 4:	#### Why 4 ? But its works :) Spanded alot of time to get fucking bug 
				# print("Trying to spawn cristal")
				Cristal(self, self.x, self.y - Cristal.size[1])

class Actor(object):
	""" Generic active game entity base class """
	spriteset = None
	def __init__(self, item_ref, x, y):
		self.x = x
		self.y = y
		self.sprite = engine.sprites[engine.get_available_sprite()]
		self.animation = engine.animations[engine.get_available_animation()]
		self.sprite.setup(self.spriteset)
		self.item = item_ref		
		actors.append(self)

	def __del__(self):
		self.animation.disable()
		self.sprite.disable()
		if self.item is not None:
			self.item.alive = False

	def kill(self):
		""" definitive kill of active game entity, removing from spawn-able item list too """
		world.objects.remove(self.item)
		self.item = None
		actors.remove(self)

class Player(Actor):
	""" main player entity """
	size = (40, 48)
	xspeed_delta = 30
	xspeed_limit = 200
	yspeed_delta = 20
	yspeed_limit = 300
	jspeed_delta = 30

	def __init__(self):
		if type(self).spriteset is None:
			type(self).spriteset = Spriteset.fromfile("Lady_Sia")

		Actor.__init__(self, None, 70, -36)
		self.respowned = False
		self.state = State.Undefined
		self.direction = Direction.Right
		self.xspeed = 0
		self.yspeed = 0
		self.weaponPicked = False
		self.set_idle()
		self.sprite.set_position(self.x, self.y)
		self.width = self.size[0]
		self.height = self.size[1]
		self.medium = Medium.Floor
		self.jump = False
		self.jump_counter = 0
		self.immunity = 0
		self.rectangle = Rectangle(0, 0, self.width, self.height)
		self.palettes = (self.spriteset.palette, Palette.fromfile("hero_alt.act"))
		self.healthBar = Healthbar()
		self.lifeBar = Lifebar()
		self.lives = 5
		self.frame = 0
		self.exploid_x = 0
		self.exploid_y = 0

	def set_idle(self):
		""" sets idle state, idempotent """	

		if self.state is not State.Idle:
			# if self.weaponPicked:
			# 	seq = "seq_idle_arm"
			# else:
			# 	seq = "seq_idle"
			seq = "seq_idle_sia"
				
			self.animation.set_sprite_animation(self.sprite.index, seq_pack.sequences[seq], 0)
			self.state = State.Idle
			self.xspeed = 0

						

	def set_running(self):
		""" sets running state, idempotent """
		if self.state is not State.Run:
		# 	if self.weaponPicked:
		# 		seq = "seq_run_arm"
		# 	else:
		# 		seq = "seq_run"

			seq = "seq_run_sia"
				
			self.animation.set_sprite_animation(self.sprite.index, seq_pack.sequences[seq], 0)
			self.state = State.Run

	def set_jump(self):
		""" sets jump state, idempotent """
	
		if self.state is not State.Jump:
			self.yspeed = -400
			# if self.weaponPicked:
			# 	seq = "seq_jump_arm"
			# else:
			# 	seq = "seq_jump"

			seq = "seq_jump_sia"

			self.animation.set_sprite_animation(self.sprite.index, seq_pack.sequences[seq], 0)
			self.state = State.Jump
			self.medium = Medium.Air
			# sounds.play("jump", 0)			

	def set_bounce(self):
		""" bounces on top of an enemy """
		self.yspeed = -150
		self.state = State.Jump
		self.medium = Medium.Air

	def set_hit(self, enemy_direction):
		""" sets hit animation by an enemy """
		self.direction = enemy_direction
		if self.direction is Direction.Left:
			self.xspeed = -self.xspeed_limit
			self.sprite.set_flags(0)
		else:
			self.xspeed = self.xspeed_limit
			self.sprite.set_flags(Flags.FLIPX)
		self.yspeed = -150
		self.state = State.Hit
		self.medium = Medium.Air
		self.animation.disable()
		self.sprite.set_picture(12)
		self.immunity = 90
		sounds.play("kick", 0)
		#######################################################################################
		self.healthBar.decreaseHp()

	##########################################
	def set_weapon(self, direction):
		""" sets weapon picked animation """
		self.direction = direction
		self.weaponPicked = True
	###########################################	

	def update_direction(self):
		""" updates sprite facing depending on direction """
		if window.get_input(Input.RIGHT):
			direction = Direction.Right
		elif window.get_input(Input.LEFT):
			direction = Direction.Left
		else:
			direction = self.direction
		if self.direction is not direction:
			self.direction = direction
			if self.direction is Direction.Right:
				self.sprite.set_flags(0)
			else:
				self.sprite.set_flags(Flags.FLIPX)

	def update_floor(self):
		""" process input when player is in floor medium """
		if not world.freezePlayer:	

			if window.get_input(Input.RIGHT) and self.xspeed < Player.xspeed_limit:
				self.xspeed += self.xspeed_delta
				self.set_running()
			elif window.get_input(Input.LEFT) and self.xspeed > -Player.xspeed_limit:
				self.xspeed -= Player.xspeed_delta
				self.set_running()
			elif abs(self.xspeed) < Player.xspeed_delta:
				self.xspeed = 0
			elif self.xspeed > 0:
				self.xspeed -= Player.xspeed_delta
			elif self.xspeed < 0:
				self.xspeed += Player.xspeed_delta
			if self.xspeed == 0:
				self.set_idle()
			
			
			if window.get_input(Input.A):
				self.jump_counter = 0 ####
				self.waitForFloor = False
				if self.jump is not True:
					player.set_jump()
					self.jump = True
					self.waitForFloor = True
				else:
					self.jump = False		

	def update_air(self):
		""" process input when player is in air medium """		
		if not world.freezePlayer:	

			if window.get_input(Input.RIGHT) and self.xspeed < Player.xspeed_limit:
				self.xspeed += self.jspeed_delta
			elif window.get_input(Input.LEFT) and self.xspeed > -Player.xspeed_limit:
				self.xspeed -= self.jspeed_delta
		

			
			if window.get_input(Input.A) and self.yspeed > 0 and self.jump_counter < 3:
				self.jump_counter += 1
				if self.jump_counter < 3:
					self.state = State.Idle
				else:
					self.state = State.Jump
				# if not self.weaponPicked:	
				# 	self.sprite.set_picture(22)
				# else:
				# 	self.sprite.set_picture(22)	
				player.set_jump()	
		
		# return True	 

	def check_left(self, x, y):
		""" checks/adjusts environment collision when player is moving to the left """
		world.foreground.get_tile(x, y + 4, tiles_info[0])
		world.foreground.get_tile(x, y + 18, tiles_info[1])
		world.foreground.get_tile(x, y + 34, tiles_info[2])
		if Tiles.Wall in (tiles_info[0].type, tiles_info[1].type, tiles_info[2].type):
			self.x = (tiles_info[0].col + 1) * 16
			self.xspeed = 0
		world.pick_gem(tiles_info)

	def check_right(self, x, y):
		""" checks/adjusts environment collision when player is moving to the right """
		world.foreground.get_tile(x + self.width, y + 4, tiles_info[0])
		world.foreground.get_tile(x + self.width, y + 18, tiles_info[1])
		world.foreground.get_tile(x + self.width, y + 34, tiles_info[2])
		if Tiles.Wall in (tiles_info[0].type, tiles_info[1].type, tiles_info[2].type):
			self.x = (tiles_info[0].col * 16) - self.width
			self.xspeed = 0
		world.pick_gem(tiles_info)

	def check_top(self, x, y):
		""" checks/adjusts environment collision when player is jumping """
		world.foreground.get_tile(x + 0, y, tiles_info[0])
		world.foreground.get_tile(x + 12, y, tiles_info[1])
		world.foreground.get_tile(x + 24, y, tiles_info[2])
		if Tiles.Wall in (tiles_info[0].type, tiles_info[1].type, tiles_info[2].type):
			self.y = (tiles_info[0].row + 1) * 16
			self.yspeed = 0
		world.pick_gem(tiles_info)

	def check_bottom(self, x, y):
		""" checks/adjusts environment collision when player is falling or running """
		ground = False

		world.foreground.get_tile(x + 0, y + self.height, tiles_info[0])
		world.foreground.get_tile(x + 12, y + self.height, tiles_info[1])
		world.foreground.get_tile(x + 24, y + self.height, tiles_info[2])
		world.foreground.get_tile(x + 12, y + self.height - 1, tiles_info[3])

		# check up slope
		if tiles_info[3].type is Tiles.SlopeUp:
			slope_height = 16 - tiles_info[3].xoffset
			if self.yspeed >= 0 and tiles_info[3].yoffset > slope_height:
				self.y -= (tiles_info[3].yoffset - slope_height)
				ground = True

		# check down slope
		elif tiles_info[3].type is Tiles.SlopeDown:
			slope_height = tiles_info[3].xoffset + 1
			if self.yspeed >= 0 and tiles_info[3].yoffset > slope_height:
				self.y -= (tiles_info[3].yoffset - slope_height)
				ground = True

		# check inner slope (avoid falling between staircased slopes)
		elif tiles_info[1].type is Tiles.InnerSlopeUp:
			if self.xspeed > 0:
				self.y = (tiles_info[1].row * 16) - self.height - 1
			else:
				self.x -= 1
			ground = True

		elif tiles_info[1].type is Tiles.InnerSlopeDown:
			if self.xspeed > 0:
				self.x += 1
			else:
				self.y = (tiles_info[1].row * 16) - self.height - 1
			ground = True

		# check regular floor
		elif Tiles.Floor in (tiles_info[0].type, tiles_info[1].type, tiles_info[2].type):
			self.y = (tiles_info[0].row * 16) - self.height
			ground = True

		# adjust to ground
		if ground is True:
			########################
			if len(list(filter(lambda e: isinstance(e, StartAnimation.__class__), actors))) == 0: # checks if StartAnimation in actors list	
				world.freezePlayer = True
			else:	
				world.freezePlayer = False
			###################################
			self.yspeed = 0
			if self.medium is Medium.Air:
				self.medium = Medium.Floor
				if self.xspeed == 0:
					self.set_idle()
				else:
					self.set_running()
		else:
			self.medium = Medium.Air
		world.pick_gem(tiles_info)

	def check_jump_on_enemies(self, x, y):
		""" checks jumping above an enemy. If so, kills it, bounces and spawns a death animation """
		px, py = x+self.width/2, y+self.height
		for actor in actors:
		 	actor_type = type(actor)
		 	if actor_type is Eagle:
		 		ex, ey = actor.x + actor.size[0]/2, actor.y
		 		if abs(px - ex) < 25 and 5 < py - ey < 20:
		 			actor.kill()
		 			self.set_bounce()
		 			Effect(actor.x, actor.y - 10, spriteset_death, seq_pack.sequences["seq_death"])
		 			sounds.play("crush", 2)
		return

	def check_hit(self, x, y, direction):
		""" returns if get hurt by enemy at select position and direction"""
		if self.immunity is 0 and self.rectangle.check_point(x, y):
			self.set_hit(direction)

	#################################
	def check_pick_cristal(self, x, y, direction):
		""" returns if get cristal at select position and direction"""
		if not self.weaponPicked and self.rectangle.check_point(x, y):
			self.set_weapon(direction)
			actor.kill()	 			
			Effect(actor.x, actor.y, spriteset_vanish, seq_pack.sequences["seq_vanish"])
			sounds.play("pickup", 1)
			self.set_jump()	

	def check_death(self):	
		if self.y > HEIGHT + player.size[1]/2:
			self.exploid_x = int(self.x)
			self.exploid_y = HEIGHT - DeathAnimation.size[0]
			self.respowned = True
			self.state = State.Undefined
			self.direction = Direction.Right
			self.xspeed = 0
			self.yspeed = 0
			self.weaponPicked = False
			# self.set_idle()
			self.immunity = 90
			self.lives -= 1
			self.x = 70
			self.y = -120
			self.lifeBar.decreaseLifes()
			self.healthBar.encreaseHp()	

	def set_death(self):		
		self.exploid_x = int(self.x)
		self.exploid_y = int(self.y - DeathAnimation.size[1]/2)
		self.respowned = True
		self.state = State.Undefined
		self.direction = Direction.Right
		self.xspeed = 0
		self.yspeed = 0
		self.weaponPicked = False
		# self.set_idle()
		self.immunity = 90
		self.lives -= 1
		self.x = 70
		self.y = -120					
	#################################		

	def update(self):
		""" process input and updates state once per frame """
		world.freezePlayer = False
		oldx = self.x
		oldy = self.y
		# update immunity
		if self.immunity is not 0:
			pal_index0 = (self.immunity >> 2) & 1
			self.immunity -= 1
			pal_index1 = (self.immunity >> 2) & 1
			if self.immunity is 0:
				pal_index1 = 0
			if pal_index0 != pal_index1:
				self.sprite.set_palette(self.palettes[pal_index1])		

		# update sprite facing
		self.update_direction()

		# user input: move character depending on medium
		
		if self.medium is Medium.Floor:
			# world.freezePlayer = False	
			self.update_floor()

		elif self.medium is Medium.Air:
			if self.state is not State.Hit:
				self.update_air()
			if self.yspeed < Player.yspeed_limit:
				self.yspeed += Player.yspeed_delta

		self.x += (self.xspeed / 100.0)
		self.y += (self.yspeed / 100.0)

		# clip to world limits
		if self.x < 0.0:
			self.x = 0.0
		elif self.x > world.foreground.width - self.width:
			self.x = world.foreground.width - self.width

		########################
		self.check_death()
									
		#######################	

		# check and fix 4-way collisions depending on motion direction
		intx = int(self.x)
		inty = int(self.y)
		if self.yspeed < 0:
			self.check_top(intx, inty)
		elif self.yspeed >= 0:
			self.check_bottom(intx, inty)
		if self.xspeed < -10:
			self.check_left(intx, inty)
		elif self.xspeed > 0:
			self.check_right(intx, inty)
		if self.yspeed > 0:
			self.check_jump_on_enemies(intx, inty)

		if self.x != oldx or self.y != oldy:
			self.rectangle.update_position(int(self.x), int(self.y))
			self.sprite.set_position(int(self.x) - world.x, int(self.y))
		####################
		return True
################################################################################################

class DeathAnimation(Actor):

	size = (100, 108)
	spriteset = None
		
	def __init__(self, x, y):
		
		if type(self).spriteset is None:
			type(self).spriteset = Spriteset.fromfile("effect_boom")
		self.frame = 0	
		Actor.__init__(self, None, 100, HEIGHT)			
		self.sprite.set_position(100, HEIGHT)
		self.animation.set_sprite_animation(self.sprite.index, seq_pack.sequences["seq_boom"], 0)
		self.flag = False


	def update(self):	
		""" Update once per frame """	
		if player.respowned:
			self.sprite.set_position(player.exploid_x - player.size[0], player.exploid_y)
			self.animation.set_sprite_animation(self.sprite.index, seq_pack.sequences["seq_boom"], 0)
			sounds.play("exlosion", 1)
			player.respowned = False		
			self.flag = True
		if self.flag:
			self.frame += 1
		if self.frame >= 118:
			self.flag = False
			self.frame = 0
			self.sprite.set_position(100, HEIGHT)
			
		return True		

class StartAnimation(Actor):

	size = (300, 150)
	spriteset = None
		
	def __init__(self):
		if type(self).spriteset is None:
			type(self).spriteset = Spriteset.fromfile("effect_start")
		self.frame = 0
		self.layer = engine.layers[1]
		Actor.__init__(self, None, 140, 50)
		self.animation.set_sprite_animation(self.sprite.index, seq_pack.sequences["seq_start"], 0)
		self.sprite.set_position(140, 50)
		sounds.play("fight", 3)

	def update(self):	
		""" Update once per frame """
		self.frame += 1
		if self.frame >= 305 or not self.animation.get_state():
			return False
		return True				

class Healthbar(Actor):

	size = (144, 70)
	partition = 12
	spriteset = None
		
	def __init__(self):
		if type(self).spriteset is None:
			type(self).spriteset = Spriteset.fromfile("hp")
		self.hpStage = self.partition
		self.frame = 0
		self.layer = engine.layers[1]
		Actor.__init__(self, None, 0, 0)
		self.animation.set_sprite_animation(self.sprite.index, seq_pack.sequences["seq_hpUp"], 0)
		self.sprite.set_position(0, 0)


	def decreaseHp(self):
		seq = "seq_hpDown" 
		if self.hpStage > 1:
			seq = seq + str(self.hpStage)
			# print(seq)
			self.animation.set_sprite_animation(self.sprite.index, seq_pack.sequences[seq], 0)
			self.hpStage -= 1
			self.frame -= 50
		else:
			player.set_death()
			player.lifeBar.decreaseLifes()
			self.hpStage = self.partition
			# self.sprite.set_picture(self.hpStage)	
			self.encreaseHp()
		return

	def encreaseHp(self):
		self.frame = 0	
		self.animation.set_sprite_animation(self.sprite.index, seq_pack.sequences["seq_hpUp"], 0)
		self.hpStage = self.partition

	def update(self):	
		""" Update once per frame """
		if self.frame >= 190:
			self.animation.disable()
			self.sprite.set_picture(self.hpStage)
		else:	
			self.frame += 1	
		return True
	
class Lifebar(Actor):

	size = (15, 15)
	spriteset = None
		
	def __init__(self):
		if type(self).spriteset is None:
			type(self).spriteset = Spriteset.fromfile("nums")
		self.lifeStage = 0
		self.frame = 0
		self.layer = engine.layers[1]
		Actor.__init__(self, None, 130, 25)
		self.animation.set_sprite_animation(self.sprite.index, seq_pack.sequences["seq_life"], 0)
		self.sprite.set_position(130, 25)


	def decreaseLifes(self):
		""" decreases num of lifes """
		self.lifeStage += 1
		self.sprite.set_picture(self.lifeStage)
		print(self.lifeStage)
		if self.lifeStage == 5:
			# player.healthBar.sprite.disable()
			# player.lifeBar.sprite.disable()
			actors.remove(player)	
		return

	def update(self):	
		""" Update once per frame """
		if self.frame >= 150:
			self.animation.disable()
			self.sprite.set_picture(self.lifeStage)
		else:	
			self.frame += 1	
		return True		
################################################################################################
class Cristal(Actor):
	"""Flying cristal """
	size = (16, 16)

	def __init__(self, item_ref, x, y):
		if type(self).spriteset is None:
			type(self).spriteset = Spriteset.fromfile("enemy_cristal")
		
		Actor.__init__(self, item_ref, x, y)
		self.frame = 0
		self.base_y = y
		self.xspeed = -3
		self.direction = Direction.Left
		self.animation.set_sprite_animation(self.sprite.index, seq_pack.sequences["seq_cristal"], 0)
		self.collision_points = (4, 20, 36)

	def update(self):	
		""" Update once per frame """
		self.x += self.xspeed
		self.y = self.base_y + int(sin(radians(self.frame*4))*15)
		self.frame += 1
		screen_x = self.x - world.x

		if self.direction is Direction.Left:
			if screen_x < 10:
				self.direction = Direction.Right
				self.xspeed = -self.xspeed
				self.sprite.set_flags(Flags.FLIPX)
			else:
				for point in self.collision_points:
					player.check_pick_cristal(self.x, self.y + point, self.direction)
		else:
			if screen_x > 650:
				self.direction = Direction.Left
				self.xspeed = -self.xspeed
				self.sprite.set_flags(0)
			else:
				for point in self.collision_points:
					player.check_pick_cristal(self.x, self.y + point, self.direction)
		self.sprite.set_position(screen_x, self.y)
		return True			
################################################################################################
			
class Eagle(Actor):
	""" Flying enemy """
	size = (40, 40)

	def __init__(self, item_ref, x, y):
		if type(self).spriteset is None:
			type(self).spriteset = Spriteset.fromfile("enemy_eagle")

		Actor.__init__(self, item_ref, x, y)
		self.frame = 0
		self.base_y = y
		self.xspeed = -3
		self.direction = Direction.Left
		self.animation.set_sprite_animation(self.sprite.index, seq_pack.sequences["seq_eagle"], 0)
		self.collision_points = (4, 20, 36)

	def update(self):
		""" Update once per frame """
		self.x += self.xspeed
		self.y = self.base_y + int(sin(radians(self.frame*4))*15)
		self.frame += 1
		# if self.frame is 10:
		# 	sounds.play("eagle", 3)
		# if self.frame < 200:
		# 	screen_x = world.x + 590
		screen_x = self.x - world.x
		# else:
		# 	screen_x = world.x + 590 + (self.x - world.x)

		if self.direction is Direction.Left:
			if screen_x < 180: #0
				self.direction = Direction.Right
				self.xspeed = -self.xspeed
				self.sprite.set_flags(Flags.FLIPX)
				if not StartAnimation:
					sounds.play("eagle", 3)
			else:
				for point in self.collision_points:
					player.check_hit(self.x, self.y + point, self.direction)
		else:
			if screen_x > 460: # 640
				self.direction = Direction.Left
				self.xspeed = -self.xspeed
				self.sprite.set_flags(0)
				# sounds.play("eagle", 3)
			else:
				for point in self.collision_points:
					player.check_hit(self.x + self.size[0], self.y + point, self.direction)
		self.sprite.set_position(screen_x, self.y)
		return True		

class Effect(Actor):
	""" placeholder for simple sprite effects """
	def __init__(self, x, y, spriteset, sequence):
		self.spriteset = spriteset
		Actor.__init__(self, None, x, y)
		self.animation.set_sprite_animation(self.sprite.index, sequence, 1)

	def update(self):
		""" updates effect state once per frame """
		self.sprite.set_position(self.x - world.x, self.y)
		if self.animation.get_state() is False:
			return False
		return True

#################################

##################################

class World(object):
	""" world/play field entity """
	def __init__(self):
		self.foreground = engine.layers[0]
		self.background = engine.layers[1]
		self.clouds = 0.0
		self.foreground.setup(Tilemap.fromfile("test.tmx"))
		self.background.setup(Tilemap.fromfile("layer_background.tmx"))
		self.x = 0
		self.x_max = self.foreground.width - WIDTH
		self.objects = load_objects("assets/test.tmx", "Eagle", 973)
		engine.set_background_color(self.background.tilemap)
		actors.append(self)
		self.freezePlayer = True
		self.flagStartAnimation = True
		

	def pick_gem(self, tiles_list):
		""" updates tilemap when player picks a gem """
		tile = Tile()
		tile.index = 0
		for tile_info in tiles_list:
			if tile_info.type is Tiles.Gem:
				self.foreground.tilemap.set_tile(tile_info.row, tile_info.col, tile)
				Effect(tile_info.col*16, tile_info.row*16, spriteset_vanish, seq_pack.sequences["seq_vanish"])
				sounds.play("pickup", 1)
				break
		del tile


	def update(self):
		""" updates world state once per frame """
		oldx = self.x
		if player.x < 240:
			self.x = 0
		else:
			self.x = int(player.x - 240)
		if self.x > self.x_max:
			self.x = self.x_max
		self.clouds += 0.1

		if self.x is not oldx:
			self.foreground.set_position(self.x, 0)
			self.background.set_position(self.x/8, 0)

		# spawn new entities from object list
		for item in self.objects:
			item.try_spawn(self.x)

		##############
		if self.flagStartAnimation and player.healthBar.frame == 100:
			actors.append(StartAnimation())
			self.flagStartAnimation = False

		# if player.state is State.Undefined:
		# 	self.freezePlayer = True

		return True

# Raster effect related functions *********************************************

def lerp(pos_x, x0, x1, fx0, fx1):
	""" integer linear interpolation """
	return fx0 + (fx1 - fx0) * (pos_x - x0) // (x1 - x0)

def interpolate_color(x, x1, x2, color1, color2):
	""" linear interpolation between two Color objects """
	r = lerp(x, x1, x2, color1.r, color2.r)
	g = lerp(x, x1, x2, color1.g, color2.g)
	b = lerp(x, x1, x2, color1.b, color2.b)
	return Color(r, g, b)

def raster_effect(line):
	""" raster effect callback, called every rendered scanline """
	if 0 <= line <= 128:
		color = interpolate_color(line, 0, 128, SKY_COLORS[0], SKY_COLORS[1])
		engine.set_background_color(color)

	if line == 0:
		world.background.set_position(int(world.clouds), 0)

	elif 160 <= line <= 208:
		pos1 = world.x//10
		pos2 = world.x//3
		xpos = lerp(line, 160, 208, pos1, pos2)
		world.background.set_position(xpos, 0)

	elif line == 256:
		world.background.set_position(world.x//2, 0)

#####################
class Sound(object):
	""" Manages sound effects """
	def __init__(self, path):		
		self._sounds = dict()
		print(path)
		if path is None:
			self.path = "./"
		else:
			self.path = path + "/"

				
	def load(self, name, filePath):
		self._sounds[name] = str(self.path + filePath)
		

	def play(self, name, channel):
		winsound.PlaySound(self._sounds[name], winsound.SND_ASYNC)	
#####################

# init engine
engine = Engine.create(WIDTH, HEIGHT, 2, 32, 32)
engine.set_load_path("assets")

# load spritesets for animation effects
spriteset_vanish = Spriteset.fromfile("effect_vanish")
spriteset_death = Spriteset.fromfile("effect_death")
spriteset_start = Spriteset.fromfile("effect_start")
spriteset_boom = Spriteset.fromfile("effect_boom")

# load sequences
seq_pack = SequencePack.fromfile("sequences.sqx")
tiles_info = (TileInfo(), TileInfo(), TileInfo(), TileInfo())

# set raster callback
engine.set_raster_callback(raster_effect)

##
sounds = Sound("assets")
sounds.load("jump", "jump.wav")
sounds.load("crush", "crunch.wav")
sounds.load("pickup", "pickup.wav")
sounds.load("hurt", "hurt.wav")
sounds.load("eagle", "vulture.wav")
sounds.load("fight", "123fight.wav")
sounds.load("exlosion", "explosion.wav")
sounds.load("kick", "kick.wav")

##
actors = list()		# list that contains every active game entity
world = World()		# world/level entity
player = Player()   # player entity
# DeathAnimation(200,200)
actors.append(DeathAnimation(200,200))


# Sound effects
# sounds = Sound(4, "assets")
# sounds.load("jump", "jump.wav")
# sounds.load("crush", "crunch.wav")
# sounds.load("pickup", "pickup.wav")
# sounds.load("hurt", "hurt.wav")
# sounds.load("eagle", "vulture.wav")
##############




window = Window.create()
# window creation & main loop
while window.process():
	for actor in actors:
		# if actor.__class__ != StartAnimation:
		# if actor.__class__ == DeathAnimation:
		# 	print(actor.__class__)
		if not actor.update():
			# if actor.__class__ == DeathAnimation:
			# 	print("not update")
			# if actor.__class__ == StartAnimation:
			# 	world.freezePlayer = False
			
			actors.remove(actor)
